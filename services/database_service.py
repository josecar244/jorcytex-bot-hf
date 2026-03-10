import os
import datetime
import logging
from typing import List, Dict, Any
from supabase.client import create_client, Client

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_SERVICE_KEY")
        self.client: Client = create_client(self.url, self.key)

    def search_similar_documents(self, embedding: List[float], match_threshold: float = 0.5, match_count: int = 3) -> str:
        """Realiza la búsqueda semántica en la tabla de documentos."""
        try:
            rpc_res = self.client.rpc("match_documents", {
                "query_embedding": embedding,
                "match_threshold": match_threshold,
                "match_count": match_count
            }).execute()
            
            contexto = "\n".join([item['content'] for item in rpc_res.data])
            return contexto if contexto else "No hay información específica disponible."
        except Exception as e:
            logger.error(f"Error en búsqueda vectorial: {e}")
            return "Error al recuperar contexto de la base de datos."

    def get_chat_history(self, wa_id: str, limit: int = 5) -> str:
        """Recupera el historial de chat del día actual para un usuario."""
        try:
            hoy = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            
            res = self.client.table("chat_history")\
                .select("role", "message")\
                .eq("wa_id", wa_id)\
                .gte("created_at", hoy)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            
            formato_historial = ""
            for msg in reversed(res.data):
                role = "Cliente" if msg['role'] == 'human' else "Asistente"
                formato_historial += f"{role}: {msg['message']}\n"
            return formato_historial
        except Exception as e:
            logger.error(f"Error recuperando historial: {e}")
            return ""

    def save_chat_interaction(self, wa_id: str, question: str, response: str):
        """Guarda la interacción en el historial."""
        try:
            self.client.table("chat_history").insert([
                {"wa_id": wa_id, "role": "human", "message": question},
                {"wa_id": wa_id, "role": "ai", "message": response}
            ]).execute()
        except Exception as e:
            logger.error(f"Error guardando interacción: {e}")

    def set_ai_status(self, wa_id: str, active: bool):
        """Gestiona el estado On/Off de la IA para un usuario."""
        try:
            self.client.table("bot_status").upsert({
                "wa_id": wa_id,
                "is_active": active,
                "updated_at": datetime.datetime.now().isoformat()
            }).execute()
        except Exception as e:
            logger.error(f"Error actualizando bot_status: {e}")

    def is_ai_enabled(self, wa_id: str) -> bool:
        """Verifica el estado de la IA."""
        try:
            res = self.client.table("bot_status").select("is_active").eq("wa_id", wa_id).execute()
            if res.data:
                return res.data[0]["is_active"]
            return True
        except Exception:
            return True
