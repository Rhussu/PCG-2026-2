from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QStackedWidget, QWidget
from textworld import EnvInfos

from controllers.chat_controller import ChatController
from controllers.graph_controller import GraphController
from interface.panels.chat_panel import ChatPanel
from interface.panels.config_panel import ConfigPanel
from interface.panels.left_panel import LeftPanel


class PrincipalPanel(QWidget):
    def __init__(
        self,
        graph_controller: GraphController,
        chat_controller: ChatController,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("DashboardContainer")
        self.chat_controller = chat_controller
        self.graph_controller = graph_controller

        layout = QHBoxLayout(self)

        panels_frame = QWidget(self)
        panels_frame.setObjectName("PanelsFrame")
        panels_layout = QHBoxLayout(panels_frame)
        panels_layout.setSpacing(0)

        self.left_panel = LeftPanel(graph_controller, chat_controller, panels_frame)
        self.panels_divider = QFrame(panels_frame)
        self.panels_divider.setObjectName("PanelsVerticalDivider")
        self.panels_divider.setFrameShape(QFrame.Shape.VLine)
        self.panels_divider.setFrameShadow(QFrame.Shadow.Plain)
        self.panels_divider.setFixedWidth(1)

        # Right side: QStackedWidget hosting ConfigPanel (index 0) and ChatPanel (index 1)
        self.right_stack = QStackedWidget(panels_frame)
        self.right_stack.setObjectName("RightStack")

        self.config_panel = ConfigPanel(self._on_start_game, self.right_stack)
        self.chat_panel = ChatPanel(
            chat_controller,
            on_configure=self._on_open_config,
            parent=self.right_stack,
        )

        self.right_stack.addWidget(self.config_panel)  # Index 0
        self.right_stack.addWidget(self.chat_panel)    # Index 1

        # Start with ConfigPanel active
        self.right_stack.setCurrentIndex(0)

        panels_layout.addWidget(self.left_panel, stretch=1)
        panels_layout.addWidget(self.panels_divider)
        panels_layout.addWidget(self.right_stack, stretch=1)

        layout.addWidget(panels_frame)

    def _on_start_game(self, game_file: str, max_episode_steps: int, request_infos: EnvInfos) -> None:
        self.chat_controller.start_game(
            game_file=game_file,
            max_episode_steps=max_episode_steps,
            request_infos=request_infos,
        )
        self.right_stack.setCurrentIndex(1)

    def _on_open_config(self) -> None:
        self.right_stack.setCurrentIndex(0)


