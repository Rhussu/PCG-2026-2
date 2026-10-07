from __future__ import annotations

"""Módulo de compatibilidad regresiva: GraphPanel ha sido reemplazado por RepresentationPanel.
Se mantiene este alias para evitar romper importaciones históricas.
"""
from interface.panels.representation_panel import RepresentationPanel

# Alias de compatibilidad regresiva
GraphPanel = RepresentationPanel
