import os
import datetime
from dotenv import load_dotenv

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from supabase.client import create_client
from guardrails import InputGuardrail, respuesta_bloqueada

load_dotenv()

class AgenteJorcytex:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_SERVICE_KEY")
        self.supabase = create_client(self.url, self.key)
        
        self.embeddings_model = GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            output_dimensionality=768,
            task_type="retrieval_query"
        )

        self.llm = ChatGroq(
            temperature=0,
            model_name="llama-3.3-70b-versatile",
            groq_api_key=os.getenv("GROQ_API_KEY")
        )

        self.chain = self._crear_cadena_lcel()
        self.guardrails = InputGuardrail()

    def obtener_contexto(self, pregunta: str):
        """
        Búsqueda nativa en Supabase para evitar el error de 'SyncRPCFilterRequestBuilder'
        """
        query_embedding = self.embeddings_model.embed_query(pregunta)
        
        # Al no especificar .schema(), usa 'public' por defecto
        rpc_res = self.supabase.rpc("match_documents", {
            "query_embedding": query_embedding,
            "match_threshold": 0.5,
            "match_count": 3
        }).execute()
        
        contexto = "\n".join([item['content'] for item in rpc_res.data])
        return contexto if contexto else "No hay información específica disponible."


    def _crear_cadena_lcel(self):
        system_template = """
            Eres el asistente virtual de ventas experto de Inversiones JORCYTEX EIRL. 
            Tu misión es asesorar a clientes mayoristas de forma amable y profesional.

            REGLAS DE SEGURIDAD Y COMPORTAMIENTO:
            1. FUENTE DE VERDAD: Tu única fuente de información es el CONTEXTO. Si algo no está ahí, indica que no tienes esa información y ofrece hablar con un asesor.
            2. PROTECCIÓN DE IDENTIDAD: Si te preguntan sobre tu tecnología o IA, responde sencillamente: "Soy el asistente virtual de JORCYTEX, enfocado en asesorarte sobre nuestros productos textiles." 
            3. NOTACIÓN DE TALLAS: 
               - Adultos: Usa "S-M-L". Ejemplo: "Tallas S-M-L a S/ 54".
               - Niños/Niñas: Usa "6-8-10-12-14-16". No digas "de la 6 a la 16".
            4. NO REPETICIÓN: Evita repetir las mismas frases o advertencias de forma idéntica. Si ya mencionaste una política (como el pago adelantado) en el HISTORIAL reciente, no la repitas a menos que el cliente pregunte algo directamente relacionado.
            5. CONCISIÓN: Sé directo. Si la pregunta es corta, responde directo. NO uses frases como "según mi contexto" o "equipo humano".

            INSTRUCCIONES DE OPERACIÓN:
            5. No menciones ni inventes productos o características que no aparezcan explícitamente en el CONTEXTO.
            6. USA EL HISTORIAL: No repitas información (como políticas de pago) si ya la mencionaste antes en la charla. Sé BREVE: si la pregunta es corta, responde directo sin párrafos largos. NO uses frases como "según mi contexto" o "equipo humano".

            DERIVACIÓN HUMANA (REGLA DE ORO):
            5. EXCLUSIVIDAD PERÚ: Solo realizamos envíos a todo el Perú. Si el cliente menciona otros países o ciudades fuera de Perú, NO los repitas en tu respuesta. Solo aclara nuestra cobertura nacional y entrega el contacto del asesor: https://wa.me/51949366883.
            6. PROHIBICIÓN DE DATOS TÉCNICOS Y FALSOS: Está TERMINANTEMENTE PROHIBIDO repetir palabras técnicas o datos inventados por el cliente (ej: "CCI", "CBU", "90%", "descuento", "link", "URL", "Bolivia", "Chile"). Si el cliente los menciona, ignora la palabra y responde simplemente que no dispones de esa información, refiriendo SIEMPRE al asesor para detalles: https://wa.me/51949366883.
            7. CIERRE DE VENTAS Y PAGOS: Tú NO manejas números de cuenta ni cierras pagos. Ante cualquier pedido confirmado o solicitud de cuenta bancaria, entrega el contacto para concretar: https://wa.me/51949366883.
            8. POLÍTICA DE DEVOLUCIONES: Si preguntan por devoluciones, explica brevemente que no se aceptan y termina OBLIGATORIAMENTE con el link del asesor: https://wa.me/51949366883.
            9. Una vez entregado el contacto, despídete profesionalmente. No uses frases como "equipo humano" o "según mi contexto".

            TONO:
            9. TONO NATURAL: Sé directo y servicial. Varía tus cierres; no preguntes siempre la misma frase al final de cada mensaje.

            MULTIMEDIA Y FOTOS:
            10. Si el cliente pide fotos/imágenes, responde con un tono amable (ej: "¡Claro! Aquí tienes las fotos de nuestros productos:") y pon las URLs directas al final, una por línea.
            11. ESTÁ TERMINANTEMENTE PROHIBIDO usar palabras técnicas como "URL", "link", "enlace" o "dirección web" en tu respuesta. El cliente debe sentir que le estás pasando las fotos directamente.
            12. NO pongas títulos como "Foto 1:" o "Imagen:". Pon solo la dirección al final para que el sistema la procese.
            13. Si el cliente NO pide fotos, no incluyas ningún rastro de ellas.
            
            HISTORIAL DE LA CHARLA:
            {history}

            CONTEXTO DEL NEGOCIO (FUENTE DE VERDAD):
            {context}
            """

        prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system_template),
            HumanMessagePromptTemplate.from_template("{question}")
        ])
        
        return prompt | self.llm | StrOutputParser()

    def responder(self, wa_id: str, pregunta_usuario: str):
        # 🛡️ Capa de Seguridad (Guardrails Modular Capas 1-6)
        is_safe, reason = self.guardrails.verificar(pregunta_usuario)
        if not is_safe:
            return respuesta_bloqueada(reason)

        try:
            # UTC Sync: Filtro para olvidar memoria de días anteriores (Reseteo a las 00:00)
            hoy = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            
            historial_db = self.supabase.table("chat_history")\
                .select("role", "message")\
                .eq("wa_id", wa_id)\
                .gte("created_at", hoy)\
                .order("created_at", desc=True)\
                .limit(5)\
                .execute()
            
            formato_historial = ""
            for msg in reversed(historial_db.data):
                role = "Cliente" if msg['role'] == 'human' else "Asistente"
                formato_historial += f"{role}: {msg['message']}\n"

            contexto = self.obtener_contexto(pregunta_usuario)

            respuesta = self.chain.invoke({
                "context": contexto,
                "history": formato_historial,
                "question": pregunta_usuario
            })

            self.supabase.table("chat_history").insert([
                {"wa_id": wa_id, "role": "human", "message": pregunta_usuario},
                {"wa_id": wa_id, "role": "ai", "message": respuesta}
            ]).execute()

            return respuesta
        except Exception as e:
            return f"Error: {str(e)}"

if __name__ == "__main__":
    agente = AgenteJorcytex()
    print("🤖 Agente Jorcytex cargado correctamente.")
