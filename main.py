import os
from fastapi import FastAPI, Request
from agente import AgenteJorcytex 
from services.message_service import MessageService
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()
agente = AgenteJorcytex()
messenger = MessageService()

@app.api_route("/", methods=["GET", "HEAD"])
async def root():
    return {"status": "online", "message": "Servidor JORCYTEX (Evolution v2) operando con MessageService"}

# Cache temporal para evitar duplicados
PROCESED_IDS = set()

@app.post("/webhook")
async def handle_message(request: Request):
    try:
        payload = await request.json()
        evento = payload.get("event")
        
        # 1. Filtro silencioso de eventos técnicos
        EVENTOS_RUIDO = ["contacts.update", "chats.update", "messages.update", "send.message", "presence.update", "chats.upsert", "chats.delete"]
        if str(evento).lower() in EVENTOS_RUIDO:
            return {"status": "technical_event_ignored"}

        if str(evento).lower() not in ["messages.upsert", "messages_upsert"]:
            print(f"ℹ️ Evento desconocido: {evento}")
            return {"status": "event_ignored"}

        # 2. Extracción de data
        data_field = payload.get("data", {})
        if isinstance(data_field, list):
            if not data_field: return {"status": "empty_list"}
            mensaje_obj = data_field[0]
        else:
            mensaje_obj = data_field

        # 🆔 ID único para evitar duplicados
        msg_id = mensaje_obj.get("key", {}).get("id")
        if msg_id in PROCESED_IDS:
            return {"status": "duplicate_ignored"}
        
        if msg_id:
            PROCESED_IDS.add(msg_id)
            if len(PROCESED_IDS) > 200: PROCESED_IDS.pop()

        # 3. Datos del remitente y contenido
        wa_id = mensaje_obj.get("key", {}).get("remoteJid", "SIN-ID")
        from_me = mensaje_obj.get("key", {}).get("fromMe", False)
        
        # Extraer texto
        texto_usuario = ""
        msg_content = mensaje_obj.get("message", {})
        if "conversation" in msg_content:
            texto_usuario = msg_content["conversation"]
        elif "extendedTextMessage" in msg_content:
            texto_usuario = msg_content["extendedTextMessage"].get("text", "")

        # 🤖 CONTROL DE INTERVENCIÓN HUMANA
        if from_me:
            if texto_usuario.strip().lower() == "!ia on":
                agente.set_ai_status(wa_id, True)
                messenger.send_text(wa_id, "🤖 IA Reactivada para este chat.")
            else:
                if texto_usuario and not texto_usuario.startswith("!"):
                    agente.set_ai_status(wa_id, False)
            return {"status": "human_intervention_handled"}

        # 🛑 VERIFICAR SI LA IA ESTÁ ACTIVA
        if not agente.is_ai_enabled(wa_id):
            return {"status": "ai_muted"}
        
        if not texto_usuario:
            return {"status": "no_text_content"}

        print(f"🔍 [WEBHOOK] Mensaje de {wa_id}: '{texto_usuario[:30]}...'")

        # 4. Generar y Enviar respuesta
        # El Agente se encarga de la lógica RAG y Seguridad
        # El Messenger se encarga de procesar el texto/imágenes y el envío
        respuesta_ai = agente.responder(wa_id, texto_usuario)
        messenger.process_and_send(wa_id, respuesta_ai)
            
    except Exception as e:
        print(f"❌ Error en webhook: {e}")
        
    return {"status": "ok"}
