"""Étape 2 agentique : analyse de contenu par complétion Mistral (function calling)."""

from .config import PolitiqueAnalyse
from .contracts import FicheAnalyse


def analyser(texte: str, categories: str, politique: PolitiqueAnalyse) -> FicheAnalyse:
    """Analyser un texte extrait : catégorie, émetteur candidat, mots-clés, résumé, attributs JSON."""
    raise NotImplementedError
