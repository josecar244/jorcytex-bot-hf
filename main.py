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

# Cache temporal para evitar duplicados
PROCESED_IDS = set()

@app.post("/webhook")
async def handle_message(request: Request):
    try:
        data = await request.json()
        evento = data.get("event")
        
        # 🆔 ID único del mensaje original de WhatsApp
        msg_id = data.get("data", {}).get("key", {}).get("id")
        
        # 1. Filtro de duplicados
        if msg_id and msg_id in PROCESED_IDS:
            return {"status": "ignored_duplicate"}
        
        # 2. Solo procesar mensajes
        if str(evento).lower() in ["messages.upsert", "messages_upsert"]:
            if msg_id:
                PROCESED_IDS.add(msg_id)
                if len(PROCESED_IDS) > 200: PROCESED_IDS.pop()

            msg_data = data.get("data", {})
            wa_id = msg_data.get("key", {}).get("remoteJid", "SIND-ID")
            from_me = msg_data.get("key", {}).get("fromMe", False)
            
            # Extraer texto del mensaje
            texto_usuario = ""
            msg_content = msg_data.get("message", {})
            if "conversation" in msg_content:
                texto_usuario = msg_content["conversation"]
            elif "extendedTextMessage" in msg_content:
                texto_usuario = msg_content["extendedTextMessage"].get("text", "")
            
            print(f"🔍 [WEBHOOK] Mensaje de {wa_id}: '{texto_usuario[:30]}...'")

            if from_me:
                return {"status": "ignored_self"}

            if not wa_id.endswith("@s.whatsapp.net") and not wa_id.endswith("@lid"):
                return {"status": "ignored_incompatible_id"}

            if not texto_usuario:
                return {"status": "no_text"}

            # 3. Generar respuesta de la IA (RAG)
            respuesta_ai = agente.responder(wa_id, texto_usuario)
            
            # 📸 EXTRAER IMÁGENES
            # Buscamos URLs que terminen en jpg, jpeg o png
            image_links = re.findall(r'(https?://\S+\.(?:jpg|jpeg|png))', respuesta_ai)
            
            # Limpiar el texto de URLs para enviarlo solo como texto
            texto_limpio = respuesta_ai
            for link in image_links:
                texto_limpio = texto_limpio.replace(link, "").strip()
            
            # Quitar saltos de línea excesivos al final
            texto_limpio = re.sub(r'\n{3,}', '\n\n', texto_limpio).strip()

            # 4. Enviar Texto Primero
            if texto_limpio:
                enviar_a_evolution(wa_id, texto_limpio)
            
            # 5. Enviar cada imagen como Media
            for link in image_links:
                enviar_imagen_a_evolution(wa_id, link)
            
        else:
            print(f"ℹ️ Evento ignorado: {evento}")
            
    except Exception as e:
        print(f"❌ Error en webhook: {e}")
        
    return {"status": "ok"}

def enviar_a_evolution(para, texto):
    url = f"{EVOLUTION_URL}/message/sendText/{EVOLUTION_INSTANCE}"
    headers = {"apikey": EVOLUTION_API_KEY, "Content-Type": "application/json"}
    
    payload = {
        "number": para, 
        "text": texto,
        "delay": 1000 
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"📤 Texto enviado a {para}: {response.status_code}")
        return response.json()
    except Exception as e:
        print(f"❌ Error enviando texto: {e}")
        return None

def enviar_imagen_a_evolution(para, url_imagen, pie_de_foto=""):
    url = f"{EVOLUTION_URL}/message/sendMedia/{EVOLUTION_INSTANCE}"
    headers = {"apikey": EVOLUTION_API_KEY, "Content-Type": "application/json"}
    
    payload = {
        "number": para,
        "mediaMessage": {
            "mediatype": "image",
            "caption": pie_de_foto,
            "media": url_imagen
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"🖼️ Imagen enviada a {para}: {response.status_code}")
        return response.json()
    except Exception as e:
        print(f"❌ Error enviando imagen: {e}")
        return None



