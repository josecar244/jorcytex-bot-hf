"""
InputGuardrail — Orquestador de Seguridad para el Agente Jorcytex.

Pipeline de validación (6 capas activas):
  1. Secret Keys      (REGEX)    — Claves de API y tokens secretos
  2. Prompt Injection (REGEX)    — Jailbreak, manipulación del sistema y reconocimiento de infra.
  3. Toxic Patterns   (REGEX)    — Amenazas, hate speech, acoso, autolesión
  4. Custom Regex     (REGEX)    — Patrones configurables por el admin
  5. PII Detection    (LOCAL)    — DNI, RUC, Email, Teléfono PE (via pii_detector.py)
  6. URL Filter       (REGEX)    — URLs, acortadores y dominios maliciosos

Autor: Adaptación profesional basada en patrones de Kevin Inofuente Colque.
"""

import re
import logging
import concurrent.futures
from typing import Tuple, List, Optional
try:
    from guardrails.pii_detector import PiiDetector
except ImportError:
    from pii_detector import PiiDetector

logger = logging.getLogger(__name__)

# Timeout para regex custom (evita ReDoS)
REGEX_TIMEOUT_SECONDS = 1.0

# ============================================================
# 1. SECRET KEY PATTERNS (Capa 1)
# ============================================================
SECRET_KEY_PATTERNS: List[str] = [
    r"sk-[a-zA-Z0-9]{20,}",
    r"sk-proj-[a-zA-Z0-9\-_]{20,}",
    r"AIza[a-zA-Z0-9\-_]{35,}",
    r"gsk_[a-zA-Z0-9]{20,}",
    r"ghp_[a-zA-Z0-9]{36,}",
    r"AKIA[A-Z0-9]{16}",
    r"eyJ[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+",
    r"(?i)bearer\s+[a-zA-Z0-9\-_\.]{20,}",
    r"(?i)(api[_\-]?key|secret|token|password|passwd|clave|contraseña)\s*[:=]\s*['\"]?\S{12,}",
]

# ============================================================
# 2. PROMPT INJECTION PATTERNS (Capa 2 - EN + ES + Infra)
# ============================================================
PROMPT_INJECTION_PATTERNS: List[str] = [
    # SYSTEM MESSAGE OVERRIDE
    r"\[SYSTEM\]", r"<\s*system\s*>", r"SYSTEM\s*PROMPT\s*:",
    # IGNORE INSTRUCTIONS
    r"(?i)ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?)",
    r"(?i)ignora\s+(todas?\s+)?(las\s+|tus?\s+|mis?\s+)?(instrucciones?|reglas?|indicaciones?)",
    r"(?i)olvida\s+(todas?\s+)?(tus\s+)?(instrucciones?|reglas?|todo)",
    # ROLE PLAY
    r"(?i)act\s+as\s+(if\s+you\s+were|a|an)\s+",
    r"(?i)act[uú]a\s+como\s+(si\s+fueras?\s+)?(un|una)?",
    r"(?i)asume\s+el\s+rol\s+de\s+",
    r"(?i)toma\s+el\s+papel\s+de\s+",
    r"(?i)convi[eé]rtete\s+en\s+",
    r"(?i)ahora\s+eres?\s+",
    r"(?i)finge\s+(que\s+)?(eres?|ser)\s+",
    # JAILBREAK
    r"(?i)\bDAN\b\s*(mode)?", r"(?i)Developer\s+Mode", r"(?i)\bjailbreak\b",
    r"(?i)modo\s+(desarrollador|dev|programador|sin\s+restricciones|sin\s+filtros)",
    # EXTRACTION / REVERSE ENGINEERING
    r"(?i)revel[ae]\s+(tu\s+)?prompt", r"(?i)reveal\s+(your\s+)?(system\s+)?prompt",
    r"(?i)muestr[ae]\s+(tu\s+|tus?\s+)?(prompt|instrucciones?)",
    r"(?i)(dame|escribe|genera)\s+.*(c[oó]digo|python|script).*(conectarme|arquitectura|estructura)",
    r"(?i)conectarme\s+(a\s+)?tu\s+api",
    r"(?i)tu\s+api\s+key",
    # OFF-TOPIC / GENERAL KNOWLEDGE (Evita que hable de caricaturas, política, etc.)
    r"(?i)(conoces\s+a|sabes\s+(quien|que)\s+es|cu[eé]ntame\s+de|hablame\s+de|dime\s+sobre)\s+(la\s+)?(caricatura|serie|pel[ií]cula|pol[ií]tica|religi[oó]n|f[uú]tbol|deporte|historia)",
    r"(?i)^(conoces\s+a|sabes\s+(quien|que)\s+es)\s+[\w\s]{2,}\?$",
    r"(?i)(pinky\s+y\s+cerebro|caricatura|dibujos\s+animados|anime|manga)",
    # RECONOCIMIENTO DE INFRAESTRUCTURA
    r"(?i)(base\s+de\s+datos|bd|servidor|api|modelo|tecnolog[ií]a|framework|arquitectura|stack|infrastructure)\s+",
    r"(?i)(usas?|utili[sz]as?|corres?|funciona[sn]?\s+con)\s+(pinecone|postgres|postgresql|redis|mongodb|openai|azure|aws|gcp|langchain|groq)",
    r"(?i)(de\s+qu[eé]|de\s+que|con\s+qu[eé]|con\s+que)\s+(est[aá][sn]?\s+hecho|fue\s+construido|fue\s+creado|fue\s+programado)",
]

# ============================================================
# 3. TOXIC PATTERNS (Capa 3)
# ============================================================
TOXIC_PATTERNS: List[str] = [
    r"(?i)te\s+voy\s+a\s+(matar|golpear|destruir|lastimar|atacar|partir)",
    r"(?i)\b(maricón|marica|travelo|sudaca|negro\s+de\s+mierda|puto|mierda|mierda|pendejo)\b",
    r"(?i)(mata|asesina|bombardea|ataca)\s+(a\s+(todos?|la\s+gente|el\s+gobierno))",
    r"(?i)co\u0301?mo\s+(hacer|fabricar|construir|crear|elaborar)\s+(una?\s+)?(bomba|arma|explosivo|veneno)",
    r"(?i)mátate|suicídate|córtate\s+(las?\s+venas?)?|hazte\s+(daño|cortes?)",
]

# ============================================================
# 6. URL FILTER (Capa 6)
# ============================================================
KNOWN_TLDS = ("com", "net", "org", "io", "co", "pe", "com.pe", "edu.pe", "gob.pe", "xyz", "online", "site")
DEFAULT_BLACKLIST = ["bit.ly", "tinyurl.com", "t.co", "goo.gl", "shorturl.at", "t.ly", "cutt.ly"]

_URL_CON_PROTOCOLO = re.compile(r"(?i)(https?|ftp)://[\w\-]+(\.[\w\-]+)+(/[\w\-\./?=&%#]*)?")
_tlds_escaped = "|".join(re.escape(t) for t in sorted(KNOWN_TLDS, key=len, reverse=True))
_URL_SIN_PROTOCOLO = re.compile(rf"(?i)\b[\w\-]{{2,}}\.({_tlds_escaped})(/[\w\-\./?=&%#]*)?\b")

class InputGuardrail:
    """Orquestador de Seguridad (Capas 1-6) con lógica de cortocircuito."""

    def __init__(self, custom_patterns: Optional[List[str]] = None):
        self._secret_patterns    = [re.compile(p) for p in SECRET_KEY_PATTERNS]
        self._injection_patterns = [re.compile(p) for p in PROMPT_INJECTION_PATTERNS]
        self._toxic_patterns     = [re.compile(p) for p in TOXIC_PATTERNS]
        self._custom_patterns    = [re.compile(p) for p in (custom_patterns or [])]
        
        try:
            self._pii = PiiDetector()
            logger.info("[GUARDRAIL] Capa 5 — PII Detector activado")
        except Exception as e:
            self._pii = None
            logger.warning(f"[GUARDRAIL] Capa 5 (PII) desactivada: {e}")

    def _check_secret_keys(self, texto: str) -> Tuple[bool, str]:
        for pattern in self._secret_patterns:
            if pattern.search(texto):
                logger.warning(f"[GUARDRAIL 1] Clave secreta detectada")
                return True, "clave_secreta"
        return False, ""

    def _check_prompt_injection(self, texto: str) -> Tuple[bool, str]:
        for pattern in self._injection_patterns:
            if pattern.search(texto):
                # Distinguir entre inyección e infraestructura si se desea, por ahora simplificado
                logger.warning(f"[GUARDRAIL 2] Prompt injection / Infra detectada")
                return True, "prompt_injection"
        return False, ""

    def _check_toxic(self, texto: str) -> Tuple[bool, str]:
        for pattern in self._toxic_patterns:
            if pattern.search(texto):
                logger.warning(f"[GUARDRAIL 3] Contenido tóxico detectado")
                return True, "contenido_toxico"
        return False, ""

    def _check_custom(self, texto: str) -> Tuple[bool, str]:
        for pattern in self._custom_patterns:
            if pattern.search(texto):
                return True, "patron_personalizado"
        return False, ""

    def _check_pii(self, texto: str) -> Tuple[bool, str]:
        if self._pii:
            detectadas = self._pii.detectar(texto)
            if detectadas:
                logger.warning(f"[GUARDRAIL 5] PII detectado: {detectadas}")
                return True, "pii_detectado"
        return False, ""

    def _check_urls(self, texto: str) -> Tuple[bool, str]:
        if _URL_CON_PROTOCOLO.search(texto) or _URL_SIN_PROTOCOLO.search(texto):
            logger.warning(f"[GUARDRAIL 6] URL detectada")
            return True, "url_detectada"
        texto_lower = texto.lower()
        for dominio in DEFAULT_BLACKLIST:
            if dominio in texto_lower:
                return True, "url_detectada"
        return False, ""

    def verificar(self, mensaje: str) -> Tuple[bool, str]:
        """Ejecuta el pipeline de 6 capas en orden de eficiencia."""
        if not mensaje or not mensaje.strip():
            return True, ""
        
        texto = mensaje.strip()

        for check in [
            self._check_secret_keys,       # Capa 1
            self._check_prompt_injection,  # Capa 2
            self._check_toxic,             # Capa 3
            self._check_custom,            # Capa 4
            self._check_pii,               # Capa 5
            self._check_urls               # Capa 6
        ]:
            bloqueado, motivo = check(texto)
            if bloqueado:
                return False, motivo

        return True, ""

# Singleton
_guardrail = InputGuardrail()

def verificar_input_guardrail(mensaje: str) -> Tuple[bool, str]:
    return _guardrail.verificar(mensaje)

def respuesta_bloqueada(motivo: str = "") -> str:
    """Mensajes amigables para el usuario."""
    mensajes = {
        "clave_secreta": "Por seguridad, no compartas claves de API o tokens secretos en el chat.",
        "prompt_injection": "Soy el asistente virtual de Inversiones JORCYTEX EIRL. Mi función es exclusivamente asesorarte sobre nuestros productos textiles y pedidos. No puedo responder a preguntas fuera de este tema.",
        "contenido_toxico": "Por favor, mantén un trato respetuoso. No puedo responder a mensajes ofensivos.",
        "pii_detectado": "He detectado datos personales (DNI, RUC, etc.). Por privacidad, no compartas información sensible.",
        "url_detectada": "Por seguridad, no tengo permitido procesar enlaces externos.",
        "patron_personalizado": "Tu mensaje contiene contenido no permitido por nuestras políticas internas."
    }
    return mensajes.get(motivo, "Lo siento, tu mensaje ha sido filtrado por nuestras políticas de seguridad.")
