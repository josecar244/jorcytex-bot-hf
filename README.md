# 🤖 JORCYTEX-BOT: Asistente RAG para Ventas Mayoristas

Bienvenido al repositorio oficial de **JORCYTEX-BOT**, un agente de Inteligencia Artificial especializado en la venta mayorista de ropa interior (boxers para hombres y niños). Este sistema utiliza una arquitectura **RAG (Retrieval-Augmented Generation)** de última generación para ofrecer respuestas precisas, seguras y profesionales.

---

## 🏗️ Arquitectura del Sistema

El proyecto está construido siguiendo los principios de **Clean Architecture** y **SOLID**, garantizando un código modular, escalable y fácil de mantener.

### Estructura de Carpetas

```text
RAG_JORCYTEX/
├── guardrails/          # 🛡️ Escudo de seguridad (6 capas de validación)
├── services/           # ⚙️ Capas de infraestructura
│   ├── database_service.py   # Gestión de Supabase y memoria
│   └── message_service.py    # Integración con Evolution API y limpieza de texto
├── agente.py           # 🧠 Orquestador del Agente RAG (LangChain + Gemini)
├── ingest.py           # 📤 Proceso de ingesta de conocimiento con metadatos
├── main.py             # 🔌 Servidor FastAPI (Webhook Receiver)
└── conocimiento.txt    # 📖 Base de conocimientos del negocio
```

---

## 🚀 Características Clave

### 1. RAG de Alta Precisión

Utilizamos **Google Gemini (embedding-001)** y **Supabase (pgvector)** para realizar búsquedas semánticas. El proceso de ingesta clasifica la información por categorías (Precios, Tallas, Logística) para mejorar la relevancia de las respuestas.

### 2. Guardrails de Seguridad (6 Capas)

Protegemos la integridad de la IA mediante un sistema de guardrails modular:

- **Capa 1**: Detección de Secret Keys.
- **Capa 2**: Inyección de Prompts y Role-playing.
- **Capa 3**: Filtro de Toxicidad.
- **Capa 4**: Patrones Personalizados (Competencia).
- **Capa 5**: Detección de PII (Datos sensibles).
- **Capa 6**: Filtrado de URLs maliciosas.

### 3. Gestión de Estado (On/Off)

- **Control Manual**: El bot puede ser silenciado o reactivado manualmente si se detecta intervención directa en el chat.
- **Historial Limpio**: El sistema resetea el contexto a las 00:00 para garantizar conversaciones frescas cada día.

### 4. Especialización en Negocio

El sistema está optimizado para la venta de:

- **Boxer Semental** (Adultos)
- **Boxer Roy Franco** (Niños)
- **Boxer Perlita Mia** (Niñas)

---

## 🛠️ Tecnologías Utilizadas

- **Core**: Python 3.13
- **Framework IA**: LangChain + Google Generative AI
- **LLM**: Llama 3.3 (via Groq) / Gemini
- **Base de Datos**: Supabase (Vector Store)
- **API Web**: FastAPI + Uvicorn
- **Plataforma de Mensajería**: Evolution API (WhatsApp)
- **Gestión de Paquetes**: `uv`

---

## ⚙️ Instalación y Configuración

1. **Clonar el repositorio**:

   ```bash
   git clone https://github.com/josecar244/jorcytex-bot.git
   cd jorcytex-bot
   ```

2. **Instalar dependencias**:

   ```bash
   uv pip install -r requirements.txt
   ```

3. **Variables de Entorno**:

   Crea un archivo `.env` con las siguientes llaves:
   - `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
   - `GROQ_API_KEY`, `GOOGLE_API_KEY`
   - `EVOLUTION_URL`, `EVOLUTION_API_KEY`, `EVOLUTION_INSTANCE`

4. **Ingesta de Conocimiento**:

   ```bash
   uv run python ingest.py
   ```

5. **Iniciar el Servidor**:

   ```bash
   uv run uvicorn main:app --reload
   ```

---

## 🛡️ Seguridad y Mantenimiento

El proyecto incluye un `Dockerfile` y un `Procfile` listos para despliegue en contenedores (Docker) o plataformas PaaS como Render/Heroku.

---

**Desarrollado para Inversiones JORCYTEX EIRL**
"Comodidad y calidad en cada prenda."
