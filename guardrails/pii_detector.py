"""
PiiDetector — Capa 5 de Seguridad: Detección de Datos Personales Sensibles (PII)
Detecta información personal en mensajes de usuarios para Perú y LATAM.
"""
import re
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# CONFIGURACIÓN DE ENTIDADES PII
PII_CONFIG: Dict[str, str] = {
    "DNI_PE":       "block",   # DNI peruano — 8 dígitos
    "RUC_PE":       "block",   # RUC — 11 dígitos
    "EMAIL":        "block",   # Correo electrónico
    "PHONE_PE":     "block",   # Teléfono peruano
    "CREDIT_CARD":  "block",   # Tarjeta de crédito/débito
}

_PII_PATTERNS = {
    "DNI_PE": re.compile(r"\b\d{8}\b"),
    "RUC_PE": re.compile(r"\b(10|15|17|20)\d{9}\b"),
    "EMAIL": re.compile(r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b"),
    "PHONE_PE": re.compile(r"(\+51|51)?\s*9\d{2}[\s\-]?\d{3}[\s\-]?\d{3}\b"),
    "CREDIT_CARD": re.compile(
        r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b"
    ),
}

class PiiDetector:
    def __init__(self, config: Optional[Dict[str, str]] = None):
        self.config = config or PII_CONFIG
        self._presidio_analyzer = None
        self._init_presidio()

    def _init_presidio(self) -> None:
        try:
            from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
            from presidio_analyzer.nlp_engine import NlpEngineProvider

            provider = NlpEngineProvider(nlp_configuration={
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "es", "model_name": "es_core_news_sm"}],
            })
            nlp_engine = provider.create_engine()
            analyzer = AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["es", "en"])

            analyzer.registry.add_recognizer(PatternRecognizer(
                supported_entity="DNI_PE",
                patterns=[Pattern("DNI_PE", r"\b\d{8}\b", 0.7)],
                supported_language="es",
            ))

            analyzer.registry.add_recognizer(PatternRecognizer(
                supported_entity="RUC_PE",
                patterns=[Pattern("RUC_PE", r"\b(10|15|17|20)\d{9}\b", 0.85)],
                supported_language="es",
            ))

            self._presidio_analyzer = analyzer
            logger.info("[PII] Presidio inicializado con reconocedores para Perú (ES)")
        except Exception as e:
            logger.warning(f"[PII] Presidio no disponible ({e}) — usando regex puro")

    def detectar(self, texto: str) -> List[str]:
        if not texto or not texto.strip():
            return []

        activas = [k for k, v in self.config.items() if v == "block"]
        if self._presidio_analyzer:
            return self._detectar_con_presidio(texto, activas)
        return self._detectar_con_regex(texto, activas)

    def _detectar_con_presidio(self, texto: str, entidades: List[str]) -> List[str]:
        try:
            resultados = self._presidio_analyzer.analyze(text=texto, language="es", entities=entidades)
            detectadas = list({r.entity_type for r in resultados if r.score >= 0.6})
            return detectadas
        except Exception:
            return self._detectar_con_regex(texto, entidades)

    def _detectar_con_regex(self, texto: str, entidades: List[str]) -> List[str]:
        detectadas = []
        for entidad in entidades:
            pattern = _PII_PATTERNS.get(entidad)
            if pattern and pattern.search(texto):
                detectadas.append(entidad)
        return detectadas
