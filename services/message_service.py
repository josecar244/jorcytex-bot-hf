import os
import re
import requests
import logging

logger = logging.getLogger(__name__)

class MessageService:
    def __init__(self):
        self.evolution_url = (os.getenv("EVOLUTION_URL") or "").rstrip("/")
        self.api_key = os.getenv("EVOLUTION_API_KEY")
        self.instance = os.getenv("EVOLUTION_INSTANCE")

    def process_and_send(self, wa_id: str, raw_response: str):
        """
        Procesa la respuesta raw de la IA, extrae imágenes, limpia el texto
        y envía todo a través de la Evolution API.
        """
        # 1. Extraer enlaces de imágenes
        image_links = re.findall(r'(https?://\S+\.(?:jpg|jpeg|png))', raw_response)

        # 2. Limpiar el texto
        texto_limpio = raw_response
        for link in image_links:
            texto_limpio = texto_limpio.replace(link, "")

        # 3. Limpieza de sobras de etiquetas (ej: "Foto:")
        lineas = texto_limpio.split("\n")
        lineas_finales = []
        for l in lineas:
            l_strip = l.strip()
            # Si la línea termina en : y es corta (probable etiqueta de foto), la saltamos
            if l_strip.endswith(":") or l_strip.endswith(":*"):
                if len(l_strip) < 30: continue 
            if l_strip:
                lineas_finales.append(l)

        texto_final = "\n".join(lineas_finales).strip()

        # 4. Enviar mensajes
        if texto_final:
            self.send_text(wa_id, texto_final)

        for link in image_links:
            self.send_image(wa_id, link)

    def send_text(self, para: str, texto: str):
        url = f"{self.evolution_url}/message/sendText/{self.instance}"
        headers = {"apikey": self.api_key, "Content-Type": "application/json"}
        payload = {
            "number": para, 
            "text": texto,
            "delay": 1000,
            "linkPreview": False
        }
        try:
            response = requests.post(url, json=payload, headers=headers)
            logger.info(f"📤 Texto enviado a {para}: {response.status_code}")
            return response.json()
        except Exception as e:
            logger.error(f"❌ Error enviando texto: {e}")
            return None

    def send_image(self, para: str, url_imagen: str, caption: str = ""):
        url = f"{self.evolution_url}/message/sendMedia/{self.instance}"
        headers = {"apikey": self.api_key, "Content-Type": "application/json"}
        payload = {
            "number": para,
            "media": url_imagen,
            "mediatype": "image",
            "caption": caption
        }
        try:
            response = requests.post(url, json=payload, headers=headers)
            logger.info(f"🖼️ Imagen enviada a {para}: {response.status_code}")
            return response.json()
        except Exception as e:
            logger.error(f"❌ Error enviando imagen: {e}")
            return None
