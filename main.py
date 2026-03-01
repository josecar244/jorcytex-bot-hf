import os
import requests
import re
from fastapi import FastAPI, Request, Response
from agente import AgenteJorcytex 
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
agente = AgenteJorcytex()

# Configuración de Evolution API
EVOLUTION_URL = os.getenv("EVOLUTION_URL") # https://evolution-api-latest-6j29.onrender.com
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY") 
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE") # El nombre que le pusiste (ej: jorcytex_v1)

@app.get("/webhook")
async def verify_webhook(request: Request):
    # Ya no es necesario para Evolution, pero lo dejamos por compatibilidad
    return {"status": "ok"}

@app.post("/webhook")
async def handle_message(request: Request):
    data = await request.json()
    
    try:
        # Evolution API manda el evento "messages.upsert"
        if data.get("event") == "messages.upsert":
            mensaje_data = data["data"]
            
            # Evitar responder a nuestros propios mensajes
            if  mensaje_data.get("key", {}).get("fromMe"):
                return {"status": "ignored"}

            wa_id = mensaje_data["key"]["remoteJid"]
            
            # Extraer el texto del usuario
            texto_usuario = ""
            if "conversation" in mensaje_data["message"]:
                texto_usuario = mensaje_data["message"]["conversation"]
            elif "extendedTextMessage" in mensaje_data["message"]:
                texto_usuario = mensaje_data["message"]["extendedTextMessage"]["text"]
            
            if not texto_usuario:
                return {"status": "no_text"}

            # Generar respuesta de la IA
            respuesta_ai = agente.responder(wa_id, texto_usuario)
            
            # Extraer links de imágenes de la respuesta
            image_links = re.findall(r'(https?://\S+\.(?:jpg|jpeg|png))', respuesta_ai)
            
            # Limpiar el texto
            texto_limpio = respuesta_ai
            for link in image_links:
                texto_limpio = texto_limpio.replace(link, "").strip()
            
            texto_limpio = re.sub(r'\n{3,}', '\n\n', texto_limpio).strip()

            # 1. Enviar el texto limpio
            if texto_limpio:
                enviar_a_evolution(wa_id, texto_limpio)
            
            # 2. Enviar cada imagen
            for link in image_links:
                enviar_imagen_a_evolution(wa_id, link)
            
    except Exception as e:
        print(f"❌ Error procesando webhook: {e}")
        
    return {"status": "ok"}

def enviar_a_evolution(para, texto):
    url = f"{EVOLUTION_URL}/message/sendText/{EVOLUTION_INSTANCE}"
    
    headers = {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "number": para,
        "text": texto,
        "delay": 1200 # Delay de 1.2 segundos para parecer humano
    }
    
    response = requests.post(url, json=payload, headers=headers)
    print(f"📤 Status Text: {response.status_code}")
    return response.json()

def enviar_imagen_a_evolution(para, url_imagen, pie_de_foto=""):
    url = f"{EVOLUTION_URL}/message/sendMedia/{EVOLUTION_INSTANCE}"
    
    headers = {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "number": para,
        "mediaMessage": {
            "mediatype": "image",
            "caption": pie_de_foto,
            "media": url_imagen
        }
    }
    
    response = requests.post(url, json=payload, headers=headers)
    print(f"🖼️ Status Image: {response.status_code}")
    return response.json()
