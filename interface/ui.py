from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect, QMainWindow, QVBoxLayout, QWidget

from controllers.chat_controller import ChatController
from controllers.graph_controller import GraphController
from interface.panels.principal_panel import PrincipalPanel
from interface.styles import APP_STYLE


class MainWindow(QMainWindow):
    def __init__(
        self,
        graph_controller: GraphController,
        chat_controller: ChatController,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Interfaz Agente IA - Profesional")
        self.resize(1580, 1080)

        root = QWidget(self)
        root.setObjectName("RootContainer")
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        self.dashboard = PrincipalPanel(graph_controller, chat_controller, root)
        layout.addWidget(self.dashboard)


def create_application() -> QApplication:
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)
    return app


