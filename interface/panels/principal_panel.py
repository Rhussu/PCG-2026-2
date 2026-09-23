from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget
from textworld import EnvInfos

from controllers.chat_controller import ChatController
from controllers.graph_controller import GraphController
from controllers.test_controller import TestRunnerWorker
from interface.panels.chat_panel import ChatPanel
from interface.panels.config_panel import ConfigPanel
from interface.panels.left_panel import LeftPanel
from interface.panels.main_menu_panel import MainMenuPanel
from interface.panels.test_progress_panel import TestProgressPanel
from interface.panels.test_results_panel import TestResultsPanel


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
        self.test_worker: TestRunnerWorker | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Root Stack:
        # Index 0: MainMenuPanel
        # Index 1: Workspace (panels_frame with LeftPanel and RightStack)
        self.root_stack = QStackedWidget(self)
        self.root_stack.setObjectName("RootStack")

        # 1. Main Menu Panel (Index 0)
        self.main_menu_panel = MainMenuPanel(
            on_open_config=self._on_menu_go_config,
            on_open_results=self._on_menu_go_results,
            parent=self.root_stack,
        )

        # 2. Workspace frame (Index 1)
        panels_frame = QWidget(self.root_stack)
        panels_frame.setObjectName("PanelsFrame")
        panels_layout = QHBoxLayout(panels_frame)
        panels_layout.setContentsMargins(0, 0, 0, 0)
        panels_layout.setSpacing(0)

        self.left_panel = LeftPanel(graph_controller, chat_controller, panels_frame)
        self.panels_divider = QFrame(panels_frame)
        self.panels_divider.setObjectName("PanelsVerticalDivider")
        self.panels_divider.setFrameShape(QFrame.Shape.VLine)
        self.panels_divider.setFrameShadow(QFrame.Shadow.Plain)
        self.panels_divider.setFixedWidth(1)

        # Right side: QStackedWidget hosting:
        # Index 0: ConfigPanel
        # Index 1: ChatPanel
        # Index 2: TestProgressPanel
        # Index 3: TestResultsPanel
        self.right_stack = QStackedWidget(panels_frame)
        self.right_stack.setObjectName("RightStack")

        self.config_panel = ConfigPanel(
            self._on_start_game,
            on_start_test=self._on_start_test,
            on_return_menu=self._on_return_to_main_menu,
            parent=self.right_stack,
        )
        self.chat_panel = ChatPanel(
            chat_controller,
            on_configure=self._on_open_config,
            on_return_menu=self._on_return_to_main_menu,
            parent=self.right_stack,
        )
        self.test_progress_panel = TestProgressPanel(
            on_open_results=self._on_open_results,
            on_open_config=self._on_open_config,
            on_open_menu=self._on_return_to_main_menu,
            parent=self.right_stack,
        )
        self.test_results_panel = TestResultsPanel(
            on_open_config=self._on_open_config,
            on_open_test=self._on_open_test,
            on_open_menu=self._on_return_to_main_menu,
            parent=self.right_stack,
        )

        self.right_stack.addWidget(self.config_panel)         # Index 0
        self.right_stack.addWidget(self.chat_panel)           # Index 1
        self.right_stack.addWidget(self.test_progress_panel)   # Index 2
        self.right_stack.addWidget(self.test_results_panel)    # Index 3

        # Conectar selección de iteración para sincronizar el mapa lateral
        self.test_progress_panel.iteration_selected.connect(self._on_iteration_selected)
        self.test_results_panel.iteration_selected.connect(self._on_iteration_selected)

        # Sincronización bidireccional de sesiones de test
        self.test_results_panel.session_changed.connect(self.test_progress_panel.load_session_data)
        self.test_progress_panel.session_selected.connect(self.test_results_panel.set_session_data)

        panels_layout.addWidget(self.left_panel, stretch=1)
        panels_layout.addWidget(self.panels_divider)
        panels_layout.addWidget(self.right_stack, stretch=1)

        # Registrar en root_stack
        self.root_stack.addWidget(self.main_menu_panel)  # Index 0
        self.root_stack.addWidget(panels_frame)          # Index 1

        # Iniciar directamente en el Menú Principal
        self.root_stack.setCurrentIndex(0)

        layout.addWidget(self.root_stack)

    def _on_start_game(self, game_file: str, max_episode_steps: int, request_infos: EnvInfos) -> None:
        self.chat_controller.start_game(
            game_file=game_file,
            max_episode_steps=max_episode_steps,
            request_infos=request_infos,
        )
        self.right_stack.setCurrentIndex(1)

    def _on_start_test(
        self,
        mode: str,
        world_config: dict,
        test_config: dict,
        max_steps: int,
        request_infos: EnvInfos,
    ) -> None:
        # Si ya había un worker corriendo, cancelarlo
        if self.test_worker and self.test_worker.isRunning():
            self.test_worker.cancel()
            self.test_worker.wait()

        self.test_worker = TestRunnerWorker(
            mode=mode,
            world_config=world_config,
            test_config=test_config,
            max_steps=max_steps,
            request_infos=request_infos,
            parent=self,
        )
        self.test_worker.test_finished.connect(self._on_test_finished)
        self.test_progress_panel.set_worker(self.test_worker)

        # Cambiar a la pantalla de testeo y arrancar el hilo
        self.right_stack.setCurrentIndex(2)
        self.test_worker.start()

    def _on_test_finished(self, session_data: dict) -> None:
        self.test_results_panel.set_session_data(session_data)
        self.test_results_panel.refresh_saved_sessions_list()
        self.test_progress_panel.refresh_saved_sessions_list()

    def _on_iteration_selected(self, iteration_data: dict) -> None:
        snapshot = iteration_data.get("map_snapshot")
        if snapshot:
            self.graph_controller.restore_snapshot(snapshot)
            self.left_panel.map_panel.refresh_map()

    def _on_open_config(self) -> None:
        self.root_stack.setCurrentIndex(1)
        self.right_stack.setCurrentIndex(0)

    def _on_open_chat(self) -> None:
        self.root_stack.setCurrentIndex(1)
        self.right_stack.setCurrentIndex(1)

    def _on_open_test(self) -> None:
        # Cargar sesión activa en la pantalla de testeo
        if self.test_results_panel.current_session:
            idx = getattr(self.test_results_panel, "selected_iteration_idx", 0)
            self.test_progress_panel.load_session_data(self.test_results_panel.current_session, idx)
        self.root_stack.setCurrentIndex(1)
        self.right_stack.setCurrentIndex(2)

    def _on_open_results(self) -> None:
        if self.test_progress_panel.latest_session_data:
            self.test_results_panel.set_session_data(self.test_progress_panel.latest_session_data)
        self.root_stack.setCurrentIndex(1)
        self.right_stack.setCurrentIndex(3)

    def _on_return_to_main_menu(self) -> None:
        self.main_menu_panel.refresh_sessions_count()
        self.root_stack.setCurrentIndex(0)

    def _on_menu_go_config(self) -> None:
        self.root_stack.setCurrentIndex(1)
        self.right_stack.setCurrentIndex(0)

    def _on_menu_go_results(self) -> None:
        self.test_results_panel.refresh_saved_sessions_list()
        self.test_progress_panel.refresh_saved_sessions_list()
        if self.test_results_panel.current_session:
            self.test_progress_panel.load_session_data(self.test_results_panel.current_session)
        self.root_stack.setCurrentIndex(1)
        self.right_stack.setCurrentIndex(3)




