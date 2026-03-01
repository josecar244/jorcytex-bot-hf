import os
import requests
import re
from fastapi import FastAPI, Request
from agente import AgenteJorcytex 
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()
agente = AgenteJorcytex()

# Configuración de Evolution API
EVOLUTION_URL = (os.getenv("EVOLUTION_URL") or "").rstrip("/") 
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY") 
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE") 

@app.get("/")
async def root():
    return {"status": "online", "message": "Servidor JORCYTEX (Evolution v2) operando"}

@app.post("/webhook")
async def handle_message(request: Request):
    try:
        data = await request.json()
        evento = data.get("event")
        
        # Super Debug: Imprimimos todo lo que sea un mensaje antes de cualquier filtro
        if str(evento).lower() in ["messages.upsert", "messages_upsert"]:
            msg_data = data.get("data", {})
            wa_id = msg_data.get("key", {}).get("remoteJid", "SIND-ID")
            from_me = msg_data.get("key", {}).get("fromMe", False)
            
            # Intentar extraer texto
            texto = ""
            msg_content = msg_data.get("message", {})
            if "conversation" in msg_content:
                texto = msg_content["conversation"]
            elif "extendedTextMessage" in msg_content:
                texto = msg_content["extendedTextMessage"].get("text", "")
            
            print(f"🔍 [WEBHOOK] Evento: {evento} | ID: {wa_id} | FromMe: {from_me} | Texto: '{texto[:30]}...'")
            
            # Filtro de salida: Ignorar si es nuestro propio mensaje
            if from_me:
                return {"status": "ignored_self"}

            # FILTRO RELAJADO: Permitimos @s.whatsapp.net y @lid
            if not wa_id.endswith("@s.whatsapp.net") and not wa_id.endswith("@lid"):
                print(f"⚠️ Ignorando ID no compatible: {wa_id}")
                return {"status": "ignored_incompatible_id"}

            if not texto:
                return {"status": "no_text"}

            # Generar IA y responder
            print(f"📩 Procesando mensaje de {wa_id}...")
            respuesta = agente.responder(wa_id, texto)
            
            # Enviar usando el JID completo (Evolution hará la conversión a número)
            enviar_a_evolution(wa_id, respuesta)
            
        else:
            print(f"ℹ️ Evento ignorado: {evento}")
            
    except Exception as e:
        print(f"❌ Error en webhook: {e}")
        
    return {"status": "ok"}

def enviar_a_evolution(para, texto):
    # Endpoint estándar de Evolution v2
    url = f"{EVOLUTION_URL}/message/sendText/{EVOLUTION_INSTANCE}"
    
    headers = {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Mandamos el JID completo (ej: 246037251891223@lid)
    # Evolution v2.3.6 resuelve estos IDs internos automáticamente.
    payload = {
        "number": para, 
        "text": texto,
        "delay": 1000 
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"📤 Respuesta enviada a {para}: {response.status_code}")
        return response.json()
    except Exception as e:
        print(f"❌ Error enviando a Evolution: {e}")
        return None


