import os
from dotenv import load_dotenv
from supabase.client import create_client
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import CharacterTextSplitter

# 1. Cargar configuración
load_dotenv()
print("🔧 Configuración cargada...")

# 2. Inicializar Supabase
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

# 3. Limpiar tabla (Ahora en public de forma segura)
print("🧹 Limpiando tabla 'documents'...")
try:
    supabase.table("documents").delete().neq("content", "vacio").execute()
except Exception as e:
    print(f"⚠️ Aviso al limpiar (puede estar vacía): {e}")

embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    task_type="retrieval_document",
    output_dimensionality=768 
)


# 5. Cargar y dividir
with open("conocimiento.txt", "r", encoding="utf-8") as f:
    text = f.read()

text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
docs = text_splitter.create_documents([text])
print(f"📖 {len(docs)} fragmentos generados.")

# 6. Indexar
print("📤 Subiendo a Supabase...")
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
