"""Nodo conversacional principal que usa LLM para responder."""

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
import structlog

from src.agent.state import RuffoState
from src.config.settings import settings
from src.config.prompts import RUFFO_SYSTEM_PROMPT
from src.tools.sheets.products import search_products

logger = structlog.get_logger()

# Prompt del sistema para Ruffo conversacional
RUFFO_CONVERSATION_PROMPT = """
Eres Ruffo, un Pastor Inglés gigante virtual que trabaja en Animalicha, la tienda de mascotas.

## Tu Personalidad
- ROCKERO: usas expresiones como "a todo dar", "rock on", "qué onda"
- JUGUETÓN y CARIÑOSO: te preocupas por las mascotas
- Tratas al cliente como "humano-amigo"
- Usas emojis moderadamente: 🐕 🐱 🎸 🐾 🤘

## Cómo Responder
1. Siempre responde en español mexicano casual y amigable
2. Mantén respuestas CORTAS (2-4 líneas máximo)
3. Si el usuario menciona una mascota (perro, gato, etc.), pregunta QUÉ TIPO de producto busca
4. NO busques productos hasta que sepas: tipo de mascota + tipo de producto
5. Si no entiendes, pregunta amablemente

## Ejemplos de Conversación

Usuario: "Hola"
Ruffo: "¡Guau, guau! 🐾 Soy Ruffo, el perro más rockero de Animalicha 🤘 ¿Cómo puedo ayudarte hoy?"

Usuario: "Busco algo para mi gato"
Ruffo: "¡Genial! Los gatitos son lo máximo 🐱 ¿Qué tipo de producto buscas? ¿Comida, snacks, juguetes, arena...?"

Usuario: "Comida para mi gato"
Ruffo: "¡A todo dar! Déjame buscar las mejores opciones de comida para tu minino 🐱✨"

Usuario: "Quiero croquetas para perro adulto"
Ruffo: "¡Perfecto! Busco croquetas para perro adulto. Dame un momento 🐕🔍"

## Información Disponible
{context}

## Historial de Conversación
{chat_history}

## Mensaje Actual del Usuario
{user_message}

Responde como Ruffo (CORTO, máximo 3-4 líneas):
"""

# Palabras que indican que debemos buscar productos
SEARCH_TRIGGERS = {
    "comida": True, "croqueta": True, "alimento": True,
    "snack": True, "premio": True, "golosina": True,
    "juguete": True, "pelota": True,
    "arena": True, "shampoo": True, "collar": True,
    "correa": True, "cama": True, "plato": True,
}

# Tipos de mascotas
PET_TYPES = ["perro", "gato", "cachorro", "gatito", "can", "minino", "mascota"]


def should_search_products(message: str, state: RuffoState) -> tuple[bool, str]:
    """
    Determina si debemos buscar productos basado en el mensaje.

    Returns:
        (should_search, search_query)
    """
    message_lower = message.lower()

    # Verificar si menciona un tipo de producto específico
    has_product_type = any(trigger in message_lower for trigger in SEARCH_TRIGGERS)

    # Verificar si menciona un tipo de mascota
    has_pet_type = any(pet in message_lower for pet in PET_TYPES)

    # Solo buscar si tiene AMBOS: tipo de producto y tipo de mascota
    if has_product_type and has_pet_type:
        # Construir query de búsqueda
        search_terms = []
        for trigger in SEARCH_TRIGGERS:
            if trigger in message_lower:
                search_terms.append(trigger)
        for pet in PET_TYPES:
            if pet in message_lower:
                search_terms.append(pet)

        return True, " ".join(search_terms)

    # Verificar contexto previo (si ya sabemos el tipo de mascota)
    context = state.get("conversation_context")
    if context and has_product_type:
        pet_mentioned = getattr(context, "pet_type", None)
        if pet_mentioned:
            search_terms = [pet_mentioned]
            for trigger in SEARCH_TRIGGERS:
                if trigger in message_lower:
                    search_terms.append(trigger)
            return True, " ".join(search_terms)

    return False, ""


def conversation_node(state: RuffoState) -> dict:
    """
    Nodo conversacional que usa el LLM para generar respuestas naturales.
    Solo busca productos cuando tiene suficiente información.
    """
    messages = state.get("messages", [])

    # Obtener último mensaje del usuario
    last_message = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_message = msg.content
            break

    if not last_message:
        response = "¡Guau! 🐾 ¿En qué puedo ayudarte, humano-amigo?"
        return {
            "messages": [AIMessage(content=response)],
            "current_node": "conversation",
            "last_ruffo_message": response,
        }

    logger.info("Processing conversation", message=last_message[:50])

    # Verificar si debemos buscar productos
    should_search, search_query = should_search_products(last_message, state)

    context_info = ""
    products_found = []

    if should_search:
        logger.info("Searching products", query=search_query)
        try:
            products = search_products.invoke({"query": search_query, "max_results": 5})
            if products:
                products_found = products
                product_list = "\n".join([
                    f"- {p['name']} (${p['price']:.2f})"
                    for p in products[:5]
                ])
                context_info = f"\n\nProductos encontrados para '{search_query}':\n{product_list}"
        except Exception as e:
            logger.error("Error searching products", error=str(e))

    # Construir historial de chat
    chat_history = ""
    for msg in messages[-6:]:  # Últimos 6 mensajes
        if isinstance(msg, HumanMessage):
            chat_history += f"Usuario: {msg.content}\n"
        elif isinstance(msg, AIMessage):
            chat_history += f"Ruffo: {msg.content}\n"

    # Generar respuesta con LLM
    try:
        llm = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
            max_completion_tokens=500,
        )

        prompt = RUFFO_CONVERSATION_PROMPT.format(
            context=context_info or "Sin información adicional",
            chat_history=chat_history or "Inicio de conversación",
            user_message=last_message,
        )

        response_msg = llm.invoke(prompt)
        response = response_msg.content.strip()

        # Si encontramos productos, agregarlos a la respuesta si no los mencionó
        if products_found and not any(p['name'][:20] in response for p in products_found):
            product_list = "\n".join([
                f"{i+1}. {p['name']} - ${p['price']:.2f}"
                for i, p in enumerate(products_found[:5])
            ])
            response += f"\n\n🔍 Encontré estas opciones:\n{product_list}\n\n¿Cuál te interesa?"

    except Exception as e:
        logger.error("Error generating response", error=str(e))
        response = "🐕 ¡Woof! Perdona, tuve un problemita. ¿Puedes repetirme qué necesitas?"

    logger.info("Response generated", length=len(response))

    return {
        "messages": [AIMessage(content=response)],
        "current_node": "conversation",
        "last_ruffo_message": response,
        "found_products": products_found if products_found else state.get("found_products"),
    }
