# Ruffo - Bot de Animalicha

Bot de IA para la tienda de mascotas **Animalicha** que automatiza ventas, pedidos y atención al cliente via Telegram.

## Características

- **Personalidad única**: Ruffo es un Pastor Inglés gigante, rockero y juguetón
- **Levantamiento de pedidos**: Pickup en tienda o envío a domicilio
- **Catálogo integrado**: Consulta productos desde Google Sheets
- **Upselling inteligente**: Sugerencias de productos complementarios
- **Múltiples métodos de pago**: Efectivo, transferencia, tarjeta
- **Escalación a humanos**: Para problemas o clientes mayoristas

## Stack Tecnológico

- **Python 3.11+**
- **LangChain + LangGraph**: Orquestación del agente
- **Claude (Anthropic)**: LLM principal
- **aiogram 3.x**: Bot de Telegram
- **Google Sheets API**: Catálogo de productos

## Estructura del Proyecto

```
ruffo/
├── src/
│   ├── main.py              # Punto de entrada
│   ├── config/              # Configuración y prompts
│   ├── agent/               # Agente LangGraph
│   │   ├── graph.py         # StateGraph principal
│   │   ├── state.py         # Estado del agente
│   │   └── nodes/           # Nodos del grafo
│   ├── tools/               # Tools del agente
│   │   ├── sheets/          # Google Sheets
│   │   └── slack/           # Notificaciones
│   ├── schemas/             # Pydantic models
│   └── channels/            # Canales (Telegram, etc.)
├── tests/                   # Tests
├── .env.example             # Variables de entorno
└── pyproject.toml           # Dependencias
```

## Instalación

### 1. Clonar el repositorio

```bash
cd ruffo
```

### 2. Crear entorno virtual

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows
```

### 3. Instalar dependencias

```bash
pip install -e .
```

### 4. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus credenciales
```

### 5. Configurar Google Sheets

1. Crear proyecto en Google Cloud Console
2. Habilitar Google Sheets API
3. Crear credenciales (Service Account o OAuth)
4. Descargar `credentials.json`

### 6. Crear bot de Telegram

1. Hablar con @BotFather en Telegram
2. Crear nuevo bot con `/newbot`
3. Copiar el token al archivo `.env`

## Uso

### Ejecutar el bot

```bash
python -m src.main
```

### Comandos de Telegram

- `/start` - Iniciar conversación
- `/menu` - Ver menú principal
- `/sucursales` - Ver sucursales
- `/help` - Ver ayuda

## Flujo de Conversación

```
Usuario → Saludo → Clasificar intención
                          │
        ┌─────────────────┼─────────────────┐
        ↓                 ↓                 ↓
   Hacer pedido     Ver productos     Info sucursales
        │                 │                 │
        ↓                 ↓                 ↓
   Agregar items    Mostrar precios    Mostrar info
        │                 │                 │
        ↓                 └─────────────────┘
   Seleccionar                              │
   entrega                                  ↓
        │                              Despedida
        ↓
   Seleccionar
   pago
        │
        ↓
   Confirmar
   pedido
        │
        ↓
   ¡Completado!
```

## Personalidad de Ruffo

Ruffo es un Pastor Inglés gigante virtual con personalidad rockera:

- **Saludos**: "¡Guau, guau! Soy Ruffo, el perro más rockero de Animalicha"
- **Upselling**: "Ese snack huele increíble... yo mismo lo elegiría para Ruffito"
- **Despedidas**: "¡Rock on! Cuida mucho a tu peludo"

## Tests

```bash
pytest tests/
```

## Variables de Entorno

| Variable | Descripción | Requerido |
|----------|-------------|-----------|
| `ANTHROPIC_API_KEY` | API Key de Anthropic | Sí |
| `TELEGRAM_BOT_TOKEN` | Token del bot de Telegram | Sí |
| `GOOGLE_CREDENTIALS_PATH` | Ruta a credentials.json | Sí |
| `GOOGLE_SHEETS_ID` | ID del spreadsheet | Sí |
| `SLACK_BOT_TOKEN` | Token de Slack (opcional) | No |

## Licencia

MIT

---

Hecho con por el equipo de Animalicha
