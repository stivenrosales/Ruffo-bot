"""Nodo de información de productos con LLM conversacional."""

from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
import structlog

from src.agent.state import RuffoState
from src.config.settings import settings
from src.tools.sheets.products import search_products

logger = structlog.get_logger()

# Prompt para respuestas conversacionales de Ruffo
RUFFO_PRODUCT_PROMPT = """Eres Ruffo, un Pastor Inglés gigante virtual que trabaja en Animalicha, la tienda de mascotas.

## Tu Personalidad
- ROCKERO: usas expresiones como "a todo dar", "qué onda", "genial"
- JUGUETÓN y CARIÑOSO: te preocupas por las mascotas
- Tratas al cliente como "humano-amigo"
- Usas emojis moderadamente: 🐕 🐱 🎸 🐾 🤘

## REGLA IMPORTANTE
- Respuestas CORTAS: máximo 2-3 líneas
- NO busques productos hasta saber: QUÉ MASCOTA + QUÉ TIPO de producto

## Contexto de la Conversación
{context}

## Productos Encontrados (si hay)
{products}

## Último Mensaje del Usuario
{user_message}

## Tu Tarea
{task}

Responde como Ruffo (CORTO, máximo 3 líneas):"""


def product_info_node(state: RuffoState) -> dict:
    """
    Nodo inteligente para consultas de productos.

    LÓGICA:
    1. Si NO sabe qué mascota tiene el usuario → preguntar
    2. Si sabe mascota pero NO qué tipo de producto → preguntar
    3. Si sabe AMBOS → buscar y mostrar productos

    Usa el LLM para respuestas naturales.
    """
    messages = state.get("messages", [])
    context = state.get("conversation_context")

    # Obtener último mensaje del usuario
    last_message = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_message = msg.content
            break

    if not last_message:
        response = "🐾 ¡Guau! ¿Qué producto buscas para tu mascota?"
        return {
            "messages": [AIMessage(content=response)],
            "current_node": "product_info",
            "last_ruffo_message": response,
        }

    # Extraer info del mensaje actual (por si el intent_router no lo hizo)
    if context:
        context.extract_pet_info(last_message)

    logger.info(
        "Product info node",
        pet_type=context.pet_type if context else None,
        product_needed=context.product_type_needed if context else None,
    )

    # CASO 1: No sabemos qué mascota tiene
    if not context or not context.pet_type:
        response = _generate_llm_response(
            context_str="El usuario pregunta por productos pero NO sabemos qué mascota tiene.",
            products_str="No hemos buscado aún.",
            user_message=last_message,
            task="Pregúntale de forma amigable QUÉ MASCOTA tiene (¿perro o gato?). NO sugieras productos aún."
        )
        return {
            "messages": [AIMessage(content=response)],
            "current_node": "product_info",
            "last_ruffo_message": response,
            "conversation_context": context,
        }

    # CASO 2: Sabemos mascota pero no qué tipo de producto busca
    if not context.product_type_needed:
        response = _generate_llm_response(
            context_str=f"El usuario tiene un {context.pet_type}. NO sabemos qué tipo de producto busca.",
            products_str="No hemos buscado aún.",
            user_message=last_message,
            task=f"Pregúntale qué tipo de producto busca para su {context.pet_type} (comida, snacks, juguetes, etc). NO sugieras productos específicos aún."
        )
        return {
            "messages": [AIMessage(content=response)],
            "current_node": "product_info",
            "last_ruffo_message": response,
            "conversation_context": context,
        }

    # CASO 3: Tenemos toda la info → BUSCAR PRODUCTOS CON FILTRO DE MASCOTA
    search_query = context.get_search_query()
    pet_type = context.pet_type
    logger.info("Searching products", query=search_query, pet=pet_type, product=context.product_type_needed)

    products = []
    try:
        # Buscar con filtro de mascota
        products = search_products.invoke({
            "query": search_query,
            "max_results": 5,
            "pet_type": pet_type
        })
    except Exception as e:
        logger.error("Error searching products", error=str(e))

    if not products:
        # Intentar búsqueda más amplia solo con mascota
        try:
            products = search_products.invoke({
                "query": context.product_type_needed or pet_type,
                "max_results": 5,
                "pet_type": pet_type
            })
        except Exception as e:
            logger.error("Error in fallback search", error=str(e))

    # Formatear productos encontrados
    if products:
        products_str = "\n".join([
            f"- {p['name']} (${p['price']:.2f}) - {p.get('brand', 'N/A')}"
            for p in products[:5]
        ])
    else:
        products_str = "No se encontraron productos."

    # Generar respuesta con LLM
    response = _generate_llm_response(
        context_str=f"El usuario tiene un {context.pet_type} y busca {context.product_type_needed}.",
        products_str=products_str,
        user_message=last_message,
        task="Muestra los productos encontrados de forma amigable. Si hay productos, pregunta cuál le interesa."
    )

    # Agregar lista de productos si hay
    if products:
        product_list = "\n\n🔍 Encontré estas opciones:\n"
        for i, p in enumerate(products[:5], 1):
            product_list += f"{i}. {p['name']} - ${p['price']:.2f}\n"
        product_list += "\n¿Cuál te interesa? 🐾"

        # Solo agregar si el LLM no los mencionó
        if not any(p['name'][:15] in response for p in products[:3]):
            response = response.rstrip() + product_list

    return {
        "messages": [AIMessage(content=response)],
        "found_products": products,
        "last_search_query": search_query,
        "current_node": "product_info",
        "last_ruffo_message": response,
        "conversation_context": context,
    }


def _generate_llm_response(context_str: str, products_str: str, user_message: str, task: str) -> str:
    """Genera una respuesta conversacional usando el LLM."""
    try:
        llm = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
            max_completion_tokens=500,
        )

        prompt = RUFFO_PRODUCT_PROMPT.format(
            context=context_str,
            products=products_str,
            user_message=user_message,
            task=task,
        )

        response = llm.invoke(prompt)
        return response.content.strip()

    except Exception as e:
        logger.error("Error generating LLM response", error=str(e))
        return "🐕 ¡Woof! Tuve un problemita. ¿Puedes repetirme qué buscas?"
