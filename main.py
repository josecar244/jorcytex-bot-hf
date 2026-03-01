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
        payload = await request.json()
        evento = payload.get("event")
        
        # 1. Filtro básico de eventos de mensaje
        if str(evento).lower() not in ["messages.upsert", "messages_upsert"]:
            print(f"ℹ️ Evento ignorado: {evento}")
            return {"status": "event_ignored"}

        # 2. Extracción segura de la data (Evolution v2 puede mandar objeto o lista)
        data_field = payload.get("data", {})
        
        # Si la data es una lista, tomamos el primer elemento (típico de Baileys/Evolution)
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
        
        if from_me: return {"status": "ignored_self"}
        
        # Extraer texto (soporte extendido)
        texto_usuario = ""
        msg_content = mensaje_obj.get("message", {})
        if "conversation" in msg_content:
            texto_usuario = msg_content["conversation"]
        elif "extendedTextMessage" in msg_content:
            texto_usuario = msg_content["extendedTextMessage"].get("text", "")
        
        if not texto_usuario:
            return {"status": "no_text_content"}

        print(f"🔍 [WEBHOOK] Mensaje de {wa_id}: '{texto_usuario[:30]}...'")

        # 4. Generar respuesta RAG
        respuesta_ai = agente.responder(wa_id, texto_usuario)
        
        # 📸 PROCESAR IMÁGENES
        # Buscamos cualquier link que termine en imagen
        image_links = re.findall(r'(https?://\S+\.(?:jpg|jpeg|png))', respuesta_ai)
        
        # Limpiar el texto: quitamos las URLs para que el mensaje se vea limpio
        texto_para_enviar = respuesta_ai
        for link in image_links:
            texto_para_enviar = texto_para_enviar.replace(link, "")
        
        # Enviamos el texto (si quedó algo después de limpiar)
        texto_para_enviar = texto_para_enviar.strip()
        if texto_para_enviar:
            enviar_a_evolution(wa_id, texto_para_enviar)
        
        # Enviamos las fotos por separado
        for link in image_links:
            enviar_imagen_a_evolution(wa_id, link)
            
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



