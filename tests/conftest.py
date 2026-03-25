# tests/conftest.py
"""
Configuration globale pytest pour le projet Knowledge Graph & RAG Assistant.
Domaine : Sportifs & compétitions
"""

import pytest


def pytest_configure(config):
    """Enregistrement des marqueurs personnalisés."""
    config.addinivalue_line(
        "markers",
        "llm: tests nécessitant un appel API LLM réel (skippés sans clé API)"
    )
    config.addinivalue_line(
        "markers",
        "slow: tests lents (chargement de la KB étendue, etc.)"
    )


def pytest_collection_modifyitems(config, items):
    """Ajoute le marqueur 'slow' aux tests qui chargent la KB étendue."""
    for item in items:
        if "graph_expanded" in getattr(item, "fixturenames", []):
            item.add_marker(pytest.mark.slow)
