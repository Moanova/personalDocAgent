"""Contrats d'interface (dataclasses) entre les modules du pipeline."""

from dataclasses import dataclass, field


@dataclass
class ResultatAcquisition:
    """Sortie de l'étape 0 : fichier accepté et son texte extrait (persisté dans conversion)."""

    fichier_source: str
    voie: str
    texte: str
    modele: str | None
    date_conversion: str


@dataclass
class FicheAnalyse:
    """Sortie de l'étape 2 agentique : décisions contraintes produites par le modèle."""

    categorie_id: int
    emetteur_candidat: str | None
    mots_cles: list[str]
    resume: str
    attributs: dict
    confiance: float

    def valider(self, nb_max_mots_cles: int) -> None:
        """Rejeter une fiche dont le nombre de mots-clés dépasse la politique d'analyse."""
        if len(self.mots_cles) > nb_max_mots_cles:
            raise ValueError(f"{len(self.mots_cles)} mots-clés > limite de {nb_max_mots_cles}")


@dataclass
class ResultatRapprochement:
    """Sortie du rapprochement d'émetteur : connu, ambigu ou inconnu."""

    statut: str
    emetteur_id: int | None = None
    libelle_propose: str | None = None


@dataclass
class FicheDocument:
    """Fiche complète assemblée avant l'étape 4 d'écriture (Dublin Core + colonnes techniques + tables filles)."""

    dc_title: str | None = None
    dc_date: str | None = None
    dc_type: str | None = None
    dc_format: str | None = None
    dc_identifier: str | None = None
    dc_language: str | None = None
    dc_rights: str | None = None
    fichier_source: str = ""
    date_ajout: str = ""
    statut: str = "actif"
    reference: str | None = None
    attributs: str = "{}"
    agents: list[tuple[str, str]] = field(default_factory=list)
    sujets: list[str] = field(default_factory=list)
    descriptions: list[str] = field(default_factory=list)
    emetteur_id: int | None = None
    categories: list[tuple[int, bool]] = field(default_factory=list)
    confiance: float = 0.0


@dataclass
class ResultatEcriture:
    """Sortie de l'étape 4 : document écrit en base ou non."""

    doc_id: int
    ecrit: bool
    raison: str | None = None


@dataclass
class FiltresRecherche:
    """Filtres de l'outil rechercher_documents (mode interrogation, lecture seule)."""

    categorie_id: int | None = None
    emetteur_id: int | None = None
    date_debut: str | None = None
    date_fin: str | None = None
    dc_type: str | None = None
    statut: str | None = None
    mot_cle: str | None = None
