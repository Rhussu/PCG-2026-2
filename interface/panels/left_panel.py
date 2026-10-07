from __future__ import annotations

from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget

from controllers.chat_controller import ChatController
from controllers.graph_controller import GraphController
from interface.panels.map_panel import MapPanel
from interface.panels.representation_panel import RepresentationPanel


class LeftPanel(QWidget):
    def __init__(
        self,
        graph_controller: GraphController,
        chat_controller: ChatController,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("LeftPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.representation_panel = RepresentationPanel(chat_controller, self)
        self.graph_panel = self.representation_panel  # retrocompatibilidad

        self.panels_divider = QFrame(self)
        self.panels_divider.setObjectName("PanelsDivider")
        self.panels_divider.setFrameShape(QFrame.Shape.HLine)
        self.panels_divider.setFrameShadow(QFrame.Shadow.Plain)
        self.panels_divider.setFixedHeight(1)

        self.map_panel = MapPanel(graph_controller, self)

        layout.addWidget(self.representation_panel, stretch=1)
        layout.addWidget(self.panels_divider)
        layout.addWidget(self.map_panel, stretch=1)

        chat_controller.state_changed.connect(self.map_panel.refresh_map)
        chat_controller.state_changed.connect(self.representation_panel.refresh_representation)

