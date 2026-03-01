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
    # 🕵️ STRATEGY: VERBOSE DEBUG LOGGING
    # We will log everything that arrives to see if Evolution API is even talking to us.
    try:
        data = await request.json()
        evento = data.get("event")
        print(f"📡 EVENTO RECIBIDO: {evento}")
        # print(f"🔍 DATOS COMPLETOS (DEBUG): {str(data)[:500]}...") # Be careful with privacy, but useful for debug
    except Exception as e:
        print(f"⚠️ Error parsing JSON: {e}")
        return {"status": "error_js_parsing"}
    
    try:
        # Evolution v2 can send 'messages.upsert' or 'MESSAGES_UPSERT' or 'messages_upsert'
        # We normalize to lowercase for safety.
        event_name = str(evento).lower()
        
        if event_name in ["messages.upsert", "messages_upsert"]:
            mensaje_data = data.get("data")
            if not mensaje_data:
                print("⚠️ Event received but 'data' field is empty.")
                return {"status": "empty_data"}
            
            # 2. Ignorar si el mensaje es nuestro (enviado por el bot)
            if mensaje_data.get("key", {}).get("fromMe"):
                print("🏠 Mensaje propio ignorado (fromMe).")
                return {"status": "ignored_self_message"}

            wa_id = mensaje_data["key"]["remoteJid"] # Ej: 51933376324@s.whatsapp.net
            
            # 🛡️ FILTRO ANTI-META / SISTEMA
            user_id = wa_id.split("@")[0]
            if len(user_id) >= 15:
                print(f"⚠️ Ignorando ID de sistema o Meta: {user_id}")
                return {"status": "ignored_system_id"}

            # 3. Extraer el texto del usuario
            texto_usuario = ""
            msg = mensaje_data.get("message", {})
            
            # En v2, el texto puede estar en varios lugares según el tipo de mensaje
            if "conversation" in msg:
                texto_usuario = msg["conversation"]
            elif "extendedTextMessage" in msg:
                texto_usuario = msg["extendedTextMessage"].get("text", "")
            
            if not texto_usuario:
                print(f"🧩 Mensaje de {user_id} recibido pero no contiene texto (ej: sticker, audio).")
                return {"status": "no_text_content"}

            print(f"📩 Mensaje de {user_id}: {texto_usuario[:50]}...")

            # 4. Generar respuesta de la IA (RAG)
            respuesta_ai = agente.responder(wa_id, texto_usuario)
            
            # 5. Enviar a través de Evolution API
            print(f"🤖 IA Responde: {respuesta_ai[:50]}...")
            enviar_a_evolution(wa_id, respuesta_ai)
            
        else:
            print(f"ℹ️ Evento ignorado (no es messages.upsert): {evento}")
            
    except Exception as e:
        print(f"❌ Error procesando webhook: {e}")
        
    return {"status": "ok"}


def enviar_a_evolution(para, texto):
    # Endpoint estándar de Evolution v2
    url = f"{EVOLUTION_URL}/message/sendText/{EVOLUTION_INSTANCE}"
    
    headers = {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json"
    }
    
    # Extraemos el número limpio por si acaso, pero mandamos el JID completo
    # si Evolution lo permite, o solo el número según la versión.
    # Para v2.3.6, mandar solo el número (sin @s.whatsapp.net) es lo más seguro.
    numero_limpio = re.sub(r'\D', '', para.split("@")[0])
    
    payload = {
        "number": numero_limpio,
        "text": texto,
        "delay": 1000 
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"� Envío a {numero_limpio}: {response.status_code}")
        return response.json()
    except Exception as e:
        print(f"❌ Error enviando a Evolution: {e}")
        return None

