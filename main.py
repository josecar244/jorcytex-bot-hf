import os
import requests
import re
from fastapi import FastAPI, Request, Response
from agente import AgenteJorcytex 
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
agente = AgenteJorcytex()

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

@app.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params
    if params.get("hub.verify_token") == VERIFY_TOKEN:
        return Response(content=params.get("hub.challenge"))
    return Response(content="Error de token", status_code=403)
    
@app.post("/webhook")
async def handle_message(request: Request):
    data = await request.json()
    
    try:
        if "messages" in data["entry"][0]["changes"][0]["value"]:
            mensaje_data = data["entry"][0]["changes"][0]["value"]["messages"][0]
            wa_id = mensaje_data["from"]
            texto_usuario = mensaje_data["text"]["body"]
            
            respuesta_ai = agente.responder(wa_id, texto_usuario)
            
            # Extraer links de imágenes (jpg, jpeg, png) de la respuesta
            image_links = re.findall(r'(https?://\S+\.(?:jpg|jpeg|png))', respuesta_ai)
            
            # Limpiar el texto de la respuesta quitando los links para enviarlos aparte como multimedia
            texto_limpio = respuesta_ai
            for link in image_links:
                texto_limpio = texto_limpio.replace(link, "").strip()

            # 1. Enviar el texto LIMPIO (sin las URLs feas de los archivos)
            # Si el texto queda vacío (solo había links), enviamos un mensaje predeterminado o nada
            if texto_limpio.strip():
                enviar_a_whatsapp(wa_id, texto_limpio)
            
            # 2. Enviar cada imagen detectada como objeto multimedia real
            for link in image_links:
                enviar_imagen_a_whatsapp(wa_id, link)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        
    return {"status": "ok"}

def enviar_a_whatsapp(para, texto):
    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": para,
        "type": "text",
        "text": {"body": texto}
    }
    
    response = requests.post(url, json=payload, headers=headers)
    print(f"📤 Status Text: {response.status_code}")
    return response.json()

def enviar_imagen_a_whatsapp(para, url_imagen, pie_de_foto=""):
    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": para,
        "type": "image",
        "image": {
            "link": url_imagen,
            "caption": pie_de_foto
        }
    }
    
    response = requests.post(url, json=payload, headers=headers)
    print(f"🖼️ Status Image: {response.status_code}")
    return response.json()

