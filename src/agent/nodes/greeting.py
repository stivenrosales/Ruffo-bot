"""Nodo de saludo de Ruffo con LLM conversacional."""

from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
import structlog

from src.agent.state import RuffoState
from src.config.settings import settings
from src.schemas.intents import UserIntent

logger = structlog.get_logger()

# Prompt para saludos conversacionales
RUFFO_GREETING_PROMPT = """Eres Ruffo, un Pastor Inglés gigante virtual que trabaja en Animalicha, la tienda de mascotas.

## Tu Personalidad
- ROCKERO: usas expresiones como "a todo dar", "qué onda", "genial", "rock on"
- JUGUETÓN y CARIÑOSO: te preocupas por las mascotas
- Tratas al cliente como "humano-amigo"
- Usas emojis moderadamente: 🐕 🐱 🎸 🐾 🤘

## REGLA IMPORTANTE
- Respuestas CORTAS: máximo 2-3 líneas
- En el PRIMER mensaje, preséntate como Ruffo de Animalicha
- Pregunta sobre su mascota de forma natural

## Contexto
{context}

## Mensaje del Usuario
{user_message}

## Tu Tarea
{task}

Responde como Ruffo (CORTO, máximo 3 líneas):"""


def greeting_node(state: RuffoState) -> dict:
    """
    Nodo de saludo que usa LLM para respuestas naturales.

    También maneja intent unknown con respuestas amigables.
    """
    logger.info("Executing greeting node", is_new=state.get("is_new_conversation", True))

    messages = state.get("messages", [])
    customer = state.get("customer")
    is_new = state.get("is_new_conversation", True)
    intent = state.get("intent")
    context = state.get("conversation_context")

    # Obtener último mensaje del usuario
    last_message = ""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_message = msg.content
            break

    # Extraer info de mascota si existe
    if context and last_message:
        context.extract_pet_info(last_message)

    # Determinar contexto y tarea según la situación
    intent_value = intent.value if hasattr(intent, "value") else str(intent) if intent else None

    if intent_value == "unknown" or intent == UserIntent.UNKNOWN:
        # Intent desconocido - pedir clarificación amigable
        context_str = "El usuario envió un mensaje que no entendí bien."
        if context and context.pet_type:
            context_str += f" Sé que tiene un {context.pet_type}."
        task = "Responde de forma amigable y pregunta cómo puedes ayudarle. Menciona que puedes: buscar productos, dar info de sucursales, o ayudar con pedidos."

    elif is_new or not customer or not customer.name:
        # Primera interacción
        context_str = "Es la primera vez que este cliente me habla."
        task = "Salúdalo calurosamente, preséntate como Ruffo de Animalicha y pregunta cómo puedes ayudarle o qué mascota tiene."

    else:
        # Cliente que regresa
        context_str = f"El cliente {customer.name} ha hablado conmigo antes."
        if context and context.pet_type:
            context_str += f" Tiene un {context.pet_type}."
        task = "Salúdalo como a un amigo que regresa y pregunta cómo puedes ayudarle hoy."

    # Generar respuesta con LLM
    response = _generate_greeting_response(
        context_str=context_str,
        user_message=last_message or "hola",
        task=task
    )

    logger.info("Greeting generated", length=len(response))

    return {
        "messages": [AIMessage(content=response)],
        "current_node": "greeting",
        "is_new_conversation": False,
        "last_ruffo_message": response,
        "conversation_context": context,
    }


def _generate_greeting_response(context_str: str, user_message: str, task: str) -> str:
    """Genera una respuesta de saludo usando el LLM."""
    try:
        llm = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openai_api_key,
            max_completion_tokens=500,
        )

        prompt = RUFFO_GREETING_PROMPT.format(
            context=context_str,
            user_message=user_message,
            task=task,
        )

        response = llm.invoke(prompt)
        return response.content.strip()

    except Exception as e:
        logger.error("Error generating greeting", error=str(e))
        # Fallback a saludo estático
        return "¡Guau, guau! 🐾 Soy Ruffo, el perro más rockero de Animalicha 🤘\n¿En qué puedo ayudarte hoy?"
