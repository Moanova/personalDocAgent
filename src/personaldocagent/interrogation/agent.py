"""Agent d'interrogation : boucle chat.completions avec function calling, historique maintenu localement."""


def interroger(question: str, historique: list | None = None) -> str:
    """Répondre à une question sur le fonds en orchestrant les outils de lecture."""
    raise NotImplementedError
