"""Interface en ligne de commande de personalDocAgent."""

import argparse
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    """Point d'entrée de la CLI personaldocagent."""
    parser = argparse.ArgumentParser(
        prog="personaldocagent",
        description="Agent documentaire personnel : indexation, classement et interrogation d'un fonds documentaire.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config"),
        help="Répertoire des fichiers YAML de configuration (défaut : ./config).",
    )
    parser.add_argument(
        "--base",
        type=Path,
        default=Path("data") / "personaldocagent.db",
        help="Chemin de la base SQLite (défaut : data/personaldocagent.db).",
    )
    sous_commandes = parser.add_subparsers(dest="commande", required=True)
    sous_commandes.add_parser("init-db", help="Créer la base SQLite à partir du schéma (T1.2).")
    sous_commandes.add_parser("charger-arbre", help="Charger la graine YAML de l'arbre de classification (T1.3).")
    sous_commandes.add_parser("pipeline", help="Exécuter le pipeline d'indexation (étapes 0-7).")
    sous_commandes.add_parser("interroger", help="Interroger le fonds en langage naturel.")

    args = parser.parse_args(argv)

    if args.commande == "init-db":
        from .db.connexion import init_db

        init_db(args.base)
        print(f"Base initialisée : {args.base}")
        return 0

    if args.commande == "charger-arbre":
        from .classification import charger_arbre
        from .db.connexion import connecter

        graine = args.config / "classification.yaml"
        conn = connecter(args.base)
        try:
            n = charger_arbre(conn, graine)
        finally:
            conn.close()
        print(f"{n} catégories chargées depuis {graine}")
        return 0

    raise NotImplementedError(
        f"Commande « {args.commande} » : à implémenter dans une tâche ultérieure de l'EPIC E1."
    )
