import os
import re
from dotenv import load_dotenv
from supabase.client import create_client
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document

# 1. Cargar configuración
load_dotenv()
print("🔧 Configuración cargada...")

# 2. Inicializar Supabase
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

# 3. Limpiar tabla
print("扫 Limpiando tabla 'documents'...")
try:
    supabase.table("documents").delete().neq("content", "vacio").execute()
except Exception as e:
    print(f"⚠️ Aviso al limpiar: {e}")

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    task_type="retrieval_document",
    output_dimensionality=768 
)

# 5. Cargar y Procesar con METADATA
print("📖 Procesando conocimiento.txt con metadatos...")
with open("conocimiento.txt", "r", encoding="utf-8") as f:
    full_text = f.read()

# Dividir por secciones basadas en encabezados en MAYÚSCULAS o que terminan en :
sections = re.split(r'\n(?=[A-Z0-9\sªº]{3,}:)', full_text)
docs = []

for section in sections:
    section = section.strip()
    if not section: continue
    
    header_match = re.match(r'^([A-Z0-9\sªº]{3,}):', section)
    category = "general"
    if header_match:
        category = header_match.group(1).lower().replace(" ", "_")
    
    # Crear documento con metadata
    doc = Document(
        page_content=section,
        metadata={"category": category, "source": "conocimiento.txt"}
    )
    docs.append(doc)

print(f"✅ {len(docs)} secciones con metadatos generadas.")

# 6. Indexar
print("📤 Subiendo a Supabase con RAG Avanzado...")
try:
    SupabaseVectorStore.from_documents(
        docs,
        embeddings,
        client=supabase,
        table_name="documents",
        query_name="match_documents"
    )
    print("✅ ¡PROCESO COMPLETADO CON ÉXITO!")
except Exception as e:
    print(f"❌ Error fatal en la subida: {e}")
