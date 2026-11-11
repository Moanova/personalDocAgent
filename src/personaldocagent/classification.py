"""Arbre de classification : chargement de la graine YAML et export aplati."""

import sqlite3
from pathlib import Path

import yaml


def charger_arbre(conn: sqlite3.Connection, graine: Path) -> int:
    """Charger la graine YAML dans la table categorie (idempotent). Retourne le nombre de catégories actives."""
    with Path(graine).open("r", encoding="utf-8") as f:
        racines = yaml.safe_load(f)
    if not isinstance(racines, list):
        raise ValueError(f"Graine invalide (liste de nœuds attendue) : {graine}")
    total = 0
    for noeud in racines:
        total += _charger_noeud(conn, noeud, parent_id=None, profondeur=1)
    conn.commit()
    return total


def _charger_noeud(conn: sqlite3.Connection, noeud: dict, parent_id: int | None, profondeur: int) -> int:
    categorie_id = _trouver_ou_creer(conn, parent_id, noeud["libelle"], profondeur)
    total = 1
    for enfant in noeud.get("enfants") or []:
        total += _charger_noeud(conn, enfant, categorie_id, profondeur + 1)
    return total


def _trouver_ou_creer(conn: sqlite3.Connection, parent_id: int | None, libelle: str, profondeur: int) -> int:
    if parent_id is None:
        row = conn.execute(
            "SELECT categorie_id FROM categorie WHERE parent_id IS NULL AND libelle = ?",
            (libelle,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT categorie_id FROM categorie WHERE parent_id = ? AND libelle = ?",
            (parent_id, libelle),
        ).fetchone()
    if row is not None:
        conn.execute(
            "UPDATE categorie SET profondeur = ?, actif = 1 WHERE categorie_id = ?",
            (profondeur, row[0]),
        )
        return row[0]
    cur = conn.execute(
        "INSERT INTO categorie (parent_id, libelle, profondeur, actif) VALUES (?, ?, ?, 1)",
        (parent_id, libelle, profondeur),
    )
    return cur.lastrowid


def exporter_aplati(conn: sqlite3.Connection) -> str:
    """Export aplati des catégories actives (id + libellé indenté par profondeur) pour le contexte de l'agent."""
    lignes = []
    for row in conn.execute(
        "SELECT categorie_id, libelle, profondeur FROM categorie WHERE actif = 1 ORDER BY categorie_id"
    ):
        lignes.append(f"{'  ' * (row['profondeur'] - 1)}{row['categorie_id']}: {row['libelle']}")
    return "\n".join(lignes)
