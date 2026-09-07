from __future__ import annotations

from PySide6.QtWidgets import QWidget


class GraphPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("GraphPanel")


