
import os
from agente import AgenteJorcytex

def simple_test():
    print("🚀 Lanzando prueba simple con Llama 3.3 70B...")
    try:
        agent = AgenteJorcytex()
        pregunta = "Hola, que productos tienes?"
        print(f"Pregunta: {pregunta}")
        
        response = agent.responder("simple_check", pregunta)
        print("\n--- Respuesta del Bot ---")
        print(response)
        print("--------------------------\n")
        
        if "Semental" in response:
            print("✅ FUNCIONA: El bot respondio con el catálogo correcto.")
        else:
            print("⚠️ El bot respondio pero revisa los datos.")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    simple_test()
