import os
from dotenv import load_dotenv
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import CharacterTextSplitter
from supabase.client import create_client

load_dotenv()

# Inicialización
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))
supabase.table("documents").delete().neq("content", "supercalifragilistico").execute()
embeddings = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    task_type="retrieval_document",
    output_dimensionality=768
)

# Carga de datos de JORCYTEX
with open("conocimiento.txt", "r", encoding="utf-8") as f:
    text = f.read()

# División en trozos
text_splitter = CharacterTextSplitter(chunk_size=600, chunk_overlap=100)
docs = text_splitter.create_documents([text])

# Subida a Supabase
vector_store = SupabaseVectorStore.from_documents(
    docs,
    embeddings,
    client=supabase,
    table_name="documents",
    query_name="match_documents",
)

print("🚀 ¡Información de JORCYTEX cargada en la tabla 'documents' con éxito!")