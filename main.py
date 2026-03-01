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
EVOLUTION_URL = (os.getenv("EVOLUTION_URL") or "").rstrip("/") 
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY") 
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE") 

@app.get("/")
async def root():
    return {"status": "online", "message": "Servidor IA de JORCYTEX operando"}

@app.get("/webhook")
async def verify_webhook(request: Request):
    # Ya no es necesario para Evolution, pero lo dejamos por compatibilidad
    return {"status": "ok"}

@app.post("/webhook")
@app.post("/webhook/{event_path:path}")
async def handle_message(request: Request, event_path: str = ""):
    data = await request.json()
    
    try:
        # Normalizar el evento: 'connection.update' o 'MESSAGES_UPSERT' -> 'MESSAGES_UPSERT'
        raw_event = data.get("event", "")
        event = raw_event.upper().replace(".", "_").replace("-", "_")
        
        if event:
            print(f"🔔 Evento detectado: {event}")
        
        # 1. Capturar el QR
        if event == "QRCODE_UPDATED":
            qr_base64 = data.get("data", {}).get("qrcode", {}).get("base64")
            if qr_base64:
                print("\n" + "="*50)
                print("📸 ¡CÓDIGO QR RECIBIDO!")
                print("Copia el texto base64 que sigue y pégalo en: https://base64-to-image.com/")
                print(qr_base64)
                print("="*50 + "\n")
            return {"status": "qr_received"}

        # 2. Procesar mensajes
        if event == "MESSAGES_UPSERT":
            mensaje_data = data["data"]
            
            # Evitar responder a nuestros propios mensajes
            if  mensaje_data.get("key", {}).get("fromMe"):
                return {"status": "ignored"}

            wa_id = mensaje_data["key"]["remoteJid"]
            
            # Extraer el texto del usuario
            texto_usuario = ""
            if mensaje_data.get("message"):
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
    
    # Limpiar el número para Evolution API (quitar @s.whatsapp.net si existe)
    numero_limpio = para.split("@")[0]
    
    payload = {
        "number": numero_limpio,
        "text": texto,
        "delay": 1200 
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"📤 Status Text: {response.status_code} - Response: {response.text}")
        return response.json()
    except Exception as e:
        print(f"❌ Error enviando a Evolution: {e}")
        return None

def enviar_imagen_a_evolution(para, url_imagen, pie_de_foto=""):
    url = f"{EVOLUTION_URL}/message/sendMedia/{EVOLUTION_INSTANCE}"
    
    headers = {
        "apikey": EVOLUTION_API_KEY,
        "Content-Type": "application/json"
    }
    
    numero_limpio = para.split("@")[0]
    
    payload = {
        "number": numero_limpio,
        "mediaMessage": {
            "mediatype": "image",
            "caption": pie_de_foto,
            "media": url_imagen
        }
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"🖼️ Status Image: {response.status_code} - Response: {response.text}")
        return response.json()
    except Exception as e:
        print(f"❌ Error enviando imagen a Evolution: {e}")
        return None
