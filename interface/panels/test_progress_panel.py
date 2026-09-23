import os
from datetime import datetime
from typing import Any, Callable

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from controllers.test_controller import (
    TestRunnerWorker,
    format_session_timestamp,
    list_saved_test_sessions,
    load_test_session,
)


class TranscriptBubble(QFrame):
    """Burbuja de diálogo para la transcripción de una partida de test."""

    def __init__(self, role: str, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        is_user = role.lower() == "user"
        self.setObjectName("UserBubble" if is_user else "AgentBubble")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        tag = QLabel("ACCION AGENTE" if is_user else "TEXTWORLD", self)
        tag.setStyleSheet("color: rgba(255,255,255,0.6); font-size: 9px; font-weight: 800; letter-spacing: 1px;")

        msg_label = QLabel(text, self)
        msg_label.setWordWrap(True)
        msg_label.setObjectName("UserText" if is_user else "AgentText")
        msg_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        layout.addWidget(tag)
        layout.addWidget(msg_label)


class TestProgressPanel(QWidget):
    """Pantalla interactiva de seguimiento del test en tiempo real,
    con visor de transcripción e integración con el mapa.
    """

    iteration_selected = Signal(dict)
    session_selected = Signal(dict)
    open_results_requested = Signal()
    open_config_requested = Signal()
    open_menu_requested = Signal()

    def __init__(
        self,
        on_open_results: Callable[[], None] | None = None,
        on_open_config: Callable[[], None] | None = None,
        on_open_menu: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("RightPanel")
        if on_open_results:
            self.open_results_requested.connect(on_open_results)
        if on_open_config:
            self.open_config_requested.connect(on_open_config)
        if on_open_menu:
            self.open_menu_requested.connect(on_open_menu)

        self.current_worker: TestRunnerWorker | None = None
        self.completed_iterations: list[dict] = []
        self.latest_session_data: dict | None = None

        self._build_ui()
        self.refresh_saved_sessions_list()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(1, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Cabecera
        root_layout.addWidget(self._build_header())

        # 2. Barra de progreso y estadísticas en vivo
        root_layout.addWidget(self._build_progress_section())

        # 3. Contenido principal: Lista de partidas + Visor de transcripción
        content_frame = QWidget(self)
        content_frame.setObjectName("TestContentFrame")
        content_layout = QHBoxLayout(content_frame)
        content_layout.setContentsMargins(20, 15, 20, 10)
        content_layout.setSpacing(15)

        splitter = QSplitter(Qt.Horizontal, content_frame)
        splitter.setChildrenCollapsible(False)

        # Sub-panel izquierdo: Lista de iteraciones
        left_box = self._build_iterations_list_widget(splitter)
        # Sub-panel derecho: Transcripción del juego
        right_box = self._build_transcript_widget(splitter)

        splitter.addWidget(left_box)
        splitter.addWidget(right_box)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 6)

        content_layout.addWidget(splitter)
        root_layout.addWidget(content_frame, stretch=1)

        # 4. Barra de acciones inferior
        root_layout.addWidget(self._build_footer())

    def _build_header(self) -> QWidget:
        header = QWidget(self)
        header.setObjectName("ConfigHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(25, 14, 25, 14)

        title_box = QVBoxLayout()
        title_box.setSpacing(3)

        tag = QLabel("BENCHMARK & EVALUACIÓN CONTINUA", header)
        tag.setObjectName("ConfigHeaderTag")

        title = QLabel("Sesión de Testeo del Agente", header)
        title.setObjectName("ConfigHeaderTitle")

        self.header_status_label = QLabel("Iniciando entorno de pruebas...", header)
        self.header_status_label.setObjectName("ConfigHeaderSubtitle")

        title_box.addWidget(tag)
        title_box.addWidget(title)
        title_box.addWidget(self.header_status_label)

        layout.addLayout(title_box)
        layout.addStretch()

        # Controles y Selector de Sesiones a la derecha
        actions_box = QVBoxLayout()
        actions_box.setSpacing(6)
        actions_box.setAlignment(Qt.AlignRight)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self.execution_badge = QLabel("📅 TEST REALIZADO: --/--/---- --:--", header)
        self.execution_badge.setObjectName("TestExecutionBadge")
        self.execution_badge.setStyleSheet(
            "background-color: rgba(89, 232, 255, 0.12); color: #59e8ff; "
            "border: 1px solid #59e8ff; border-radius: 6px; padding: 4px 10px; font-size: 11px; font-weight: 700;"
        )

        self.cancel_button = QPushButton("DETENER TEST", header)
        self.cancel_button.setObjectName("TestCancelButton")
        self.cancel_button.setCursor(Qt.PointingHandCursor)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)

        top_row.addWidget(self.execution_badge)
        top_row.addWidget(self.cancel_button)

        selector_row = QHBoxLayout()
        selector_row.setSpacing(8)
        lbl_sel = QLabel("📁 SESIÓN:", header)
        lbl_sel.setStyleSheet("color: #abb2bf; font-size: 11px; font-weight: 700;")
        self.sessions_combo = QComboBox(header)
        self.sessions_combo.setObjectName("ConfigComboBox")
        self.sessions_combo.setMinimumWidth(320)
        self.sessions_combo.currentIndexChanged.connect(self._on_session_combo_changed)

        selector_row.addWidget(lbl_sel)
        selector_row.addWidget(self.sessions_combo)

        actions_box.addLayout(top_row)
        actions_box.addLayout(selector_row)

        layout.addLayout(actions_box)
        return header

    def _build_progress_section(self) -> QWidget:
        section = QFrame(self)
        section.setObjectName("TestProgressSection")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(25, 15, 25, 15)
        layout.setSpacing(12)

        # Fila superior de progreso
        prog_header_layout = QHBoxLayout()
        self.progress_title_label = QLabel("PROGRESO GENERAL: 0%", section)
        self.progress_title_label.setObjectName("TestProgressTitle")

        self.time_label = QLabel("⏱ Tiempo: 00:00 • Estimado (ETA): --:--", section)
        self.time_label.setObjectName("TestProgressTimer")

        prog_header_layout.addWidget(self.progress_title_label)
        prog_header_layout.addStretch()
        prog_header_layout.addWidget(self.time_label)
        layout.addLayout(prog_header_layout)

        # Barra de progreso
        self.progress_bar = QProgressBar(section)
        self.progress_bar.setObjectName("TestProgressBar")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(12)
        layout.addWidget(self.progress_bar)

        # Fila de métricas clave en vivo
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(10)

        self.card_runs = self._create_kpi_card("VUELTAS", "0 / 0", "#59e8ff")
        self.card_win_rate = self._create_kpi_card("TASA VICTORIAS", "0.0%", "#98c379")
        self.card_avg_steps = self._create_kpi_card("PASOS PROMEDIO", "--", "#e5c07b")
        self.card_avg_score = self._create_kpi_card("PUNTAJE MEDIO", "--", "#c678dd")

        cards_layout.addWidget(self.card_runs)
        cards_layout.addWidget(self.card_win_rate)
        cards_layout.addWidget(self.card_avg_steps)
        cards_layout.addWidget(self.card_avg_score)
        layout.addLayout(cards_layout)

        return section

    def _create_kpi_card(self, title: str, initial_value: str, color: str) -> QFrame:
        card = QFrame()
        card.setObjectName("TestKpiCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)

        lbl_title = QLabel(title)
        lbl_title.setObjectName("TestKpiTitle")

        lbl_val = QLabel(initial_value)
        lbl_val.setObjectName("TestKpiValue")
        lbl_val.setStyleSheet(f"color: {color}; font-size: 16px; font-weight: 800;")

        layout.addWidget(lbl_title)
        layout.addWidget(lbl_val)
        card.value_label = lbl_val  # type: ignore[attr-defined]
        return card

    def _build_iterations_list_widget(self, parent: QWidget) -> QWidget:
        box = QFrame(parent)
        box.setObjectName("TestListContainer")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        lbl = QLabel("VUELTAS COMPLETADAS", box)
        lbl.setObjectName("ConfigSectionHeader")
        layout.addWidget(lbl)

        self.iterations_list = QListWidget(box)
        self.iterations_list.setObjectName("TestIterationsList")
        self.iterations_list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.iterations_list)

        hint = QLabel("💡 Selecciona una vuelta para ver su transcripción y mapa", box)
        hint.setObjectName("ConfigHintLabel")
        layout.addWidget(hint)

        return box

    def _build_transcript_widget(self, parent: QWidget) -> QWidget:
        box = QFrame(parent)
        box.setObjectName("TestTranscriptContainer")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header de la transcripción
        top_bar = QHBoxLayout()
        self.transcript_info_label = QLabel("DETALLES DE LA PARTIDA", box)
        self.transcript_info_label.setObjectName("ConfigSectionHeader")

        top_bar.addWidget(self.transcript_info_label)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        # Banner resumen de la iteración seleccionada
        self.run_summary_banner = QLabel("Selecciona una vuelta para inspeccionar los pasos.", box)
        self.run_summary_banner.setObjectName("TestRunBanner")
        layout.addWidget(self.run_summary_banner)

        # Área de mensajes de chat
        self.scroll_area = QScrollArea(box)
        self.scroll_area.setObjectName("MessagesArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.messages_container = QWidget(self.scroll_area)
        self.messages_container.setObjectName("MessagesContainer")
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(15, 15, 15, 15)
        self.messages_layout.setSpacing(10)
        self.messages_layout.addStretch()

        self.scroll_area.setWidget(self.messages_container)
        layout.addWidget(self.scroll_area, stretch=1)

        return box

    def _build_footer(self) -> QWidget:
        footer = QWidget(self)
        footer.setObjectName("ConfigActionBar")
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(25, 14, 25, 14)
        layout.setSpacing(15)

        self.footer_status = QLabel("Preparado para ejecutar test", footer)
        self.footer_status.setObjectName("ConfigStatusLabel")
        layout.addWidget(self.footer_status, stretch=1)

        self.btn_back_menu = QPushButton("🏠 MENÚ", footer)
        self.btn_back_menu.setObjectName("HeaderControl")
        self.btn_back_menu.setCursor(Qt.PointingHandCursor)
        self.btn_back_menu.clicked.connect(self.open_menu_requested.emit)

        self.btn_back_config = QPushButton("CONFIGURACIÓN", footer)
        self.btn_back_config.setObjectName("HeaderControl")
        self.btn_back_config.setCursor(Qt.PointingHandCursor)
        self.btn_back_config.clicked.connect(self.open_config_requested.emit)

        self.btn_view_results = QPushButton("VER RESULTADOS Y ANÁLISIS ➔", footer)
        self.btn_view_results.setObjectName("ConfigStartButton")
        self.btn_view_results.setCursor(Qt.PointingHandCursor)
        self.btn_view_results.setMinimumHeight(42)
        self.btn_view_results.clicked.connect(self.open_results_requested.emit)

        layout.addWidget(self.btn_back_menu)
        layout.addWidget(self.btn_back_config)
        layout.addWidget(self.btn_view_results)
        return footer

    # ------------------ Conexión de Worker y Eventos ------------------
    # ------------------ Gestión de Sesiones y Datos Históricos ------------------
    def refresh_saved_sessions_list(self) -> None:
        """Carga y actualiza el desplegable con las sesiones disponibles en disco."""
        self.sessions_combo.blockSignals(True)
        self.sessions_combo.clear()

        sessions = list_saved_test_sessions()
        for s in sessions:
            label = f"📅 {s['formatted_timestamp']} • {s['total_runs']} vueltas ({s['win_rate']}%)"
            self.sessions_combo.addItem(label, s["filepath"])

        self.sessions_combo.blockSignals(False)

        # Si hay sesiones y no hay una cargada ni un worker activo, cargar la más reciente
        if sessions and self.latest_session_data is None and self.current_worker is None:
            self.load_session_from_file(sessions[0]["filepath"])

    def _on_session_combo_changed(self, idx: int) -> None:
        if idx >= 0:
            filepath = self.sessions_combo.itemData(idx)
            if filepath and os.path.exists(filepath):
                self.load_session_from_file(filepath)

    def load_session_from_file(self, filepath: str) -> None:
        try:
            data = load_test_session(filepath)
            self.load_session_data(data)
            self.session_selected.emit(data)
        except Exception as exc:
            self.footer_status.setText(f"Error cargando sesión: {exc}")

    def load_session_data(self, session_data: dict, select_iteration_idx: int = 0) -> None:
        """Carga y ajusta la pantalla de testeo por completo para una sesión de test dada,
        mostrando cuándo pasó el testeo, sus métricas, iteraciones y transcripciones.
        """
        self.latest_session_data = session_data
        summary = session_data.get("summary", {})
        its = session_data.get("iterations", [])
        self.completed_iterations = list(its)
        mode = session_data.get("mode", "personalizado")
        ts = session_data.get("timestamp", "")
        formatted_ts = format_session_timestamp(ts)
        dur_s = summary.get("total_duration_s", 0)
        total_runs = summary.get("total_runs", len(its))
        target_runs = summary.get("target_runs", total_runs)

        # 1. Cabecera y Badge de Cuándo Pasó el Test
        self.cancel_button.setVisible(False)
        self.execution_badge.setText(f"📅 EJECUTADO: {formatted_ts} • Duración: {dur_s}s")
        self.execution_badge.setStyleSheet(
            "background-color: rgba(89, 232, 255, 0.12); color: #59e8ff; "
            "border: 1px solid #59e8ff; border-radius: 6px; padding: 4px 10px; font-size: 11px; font-weight: 700;"
        )
        self.header_status_label.setText(
            f"Modo: {mode.upper()} • {total_runs} partidas evaluadas • Fecha: {formatted_ts}"
        )

        # 2. Barra de Progreso y Cronómetro
        self.progress_bar.setValue(100)
        self.progress_title_label.setText(f"PROGRESO GENERAL: 100% • TEST FINALIZADO ({total_runs} de {target_runs} vueltas)")
        m_dur, s_dur = divmod(int(dur_s), 60)
        self.time_label.setText(f"⏱ Duración total: {m_dur:02d}:{s_dur:02d} • 📅 Fecha: {formatted_ts}")

        # 3. KPI Cards
        win_rate = summary.get("win_rate_percent", 0.0)
        avg_steps = summary.get("avg_steps", 0)
        avg_score = summary.get("avg_score", 0.0)
        self.card_runs.value_label.setText(f"{total_runs} / {target_runs}")
        self.card_win_rate.value_label.setText(f"{win_rate}%")
        self.card_avg_steps.value_label.setText(str(avg_steps))
        self.card_avg_score.value_label.setText(str(avg_score))

        # 4. Lista de Iteraciones
        self.iterations_list.clear()
        for it in its:
            it_num = it.get("iteration", 0)
            status = it.get("status", "Completado")
            steps = it.get("steps", 0)
            score = it.get("score", 0)
            dur = it.get("duration", 0)
            icon = "🏆" if it.get("won") else ("💀" if it.get("lost") else "⏳")
            item_text = f"{icon} Vuelta #{it_num} • {status} • {steps} pasos • Score {score} ({dur}s)"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, it)
            self.iterations_list.addItem(item)

        # 5. Seleccionar automáticamente la vuelta solicitada (o la primera)
        if self.iterations_list.count() > 0:
            target_idx = max(0, min(select_iteration_idx, self.iterations_list.count() - 1))
            self.iterations_list.setCurrentRow(target_idx)
            self._display_iteration(its[target_idx])
        else:
            self._clear_transcript()
            self.run_summary_banner.setText("Esta sesión no contiene vueltas registradas.")

        # 6. Sincronizar desplegable sin bucles
        saved_fp = session_data.get("saved_filepath", "")
        self.sessions_combo.blockSignals(True)
        for i in range(self.sessions_combo.count()):
            if self.sessions_combo.itemData(i) == saved_fp:
                self.sessions_combo.setCurrentIndex(i)
                break
        self.sessions_combo.blockSignals(False)

        # 7. Pie y Botón de Resultados
        self.footer_status.setText(f"Sesión cargada: {os.path.basename(saved_fp)} • Ejecutada el {formatted_ts}")
        self.btn_view_results.setText("VER RESULTADOS Y ANÁLISIS ➔")
        self.btn_view_results.setStyleSheet(
            "background-color: #98c379; color: #1e2227; font-weight: 800; font-size: 13px;"
        )

    # ------------------ Conexión de Worker y Eventos en Vivo ------------------
    def set_worker(self, worker: TestRunnerWorker) -> None:
        """Conecta un nuevo TestRunnerWorker para monitorear el test en tiempo real."""
        self.current_worker = worker
        self.completed_iterations.clear()
        self.iterations_list.clear()
        self._clear_transcript()

        now_str = datetime.now().strftime("%H:%M:%S")

        self.cancel_button.setVisible(True)
        self.cancel_button.setEnabled(True)
        self.cancel_button.setText("DETENER TEST")
        self.execution_badge.setText(f"🔴 TEST EN VIVO • Iniciado: {now_str}")
        self.execution_badge.setStyleSheet(
            "background-color: rgba(224, 108, 117, 0.15); color: #e06c75; "
            "border: 1px solid #e06c75; border-radius: 6px; padding: 4px 10px; font-size: 11px; font-weight: 700;"
        )

        self.progress_bar.setValue(0)
        self.header_status_label.setText("Ejecutando test en tiempo real...")
        self.footer_status.setText("Test en curso...")

        worker.iteration_started.connect(self._on_iteration_started)
        worker.step_progress.connect(self._on_step_progress)
        worker.iteration_completed.connect(self._on_iteration_completed)
        worker.progress_updated.connect(self._on_progress_updated)
        worker.test_finished.connect(self._on_test_finished)
        worker.test_error.connect(self._on_test_error)

    def _on_iteration_started(self, it_num: int, total_its: int) -> None:
        self.header_status_label.setText(f"Ejecutando Vuelta {it_num} de {total_its}...")
        self.footer_status.setText(f"Simulando partida autónoma {it_num}...")

    def _on_step_progress(self, it_num: int, step: int, max_steps: int) -> None:
        self.footer_status.setText(f"Vuelta {it_num} • Paso {step}/{max_steps}")

    def _on_iteration_completed(self, it_data: dict) -> None:
        self.completed_iterations.append(it_data)
        it_num = it_data["iteration"]
        status = it_data["status"]
        steps = it_data["steps"]
        score = it_data["score"]
        dur = it_data["duration"]

        icon = "🏆" if it_data["won"] else ("💀" if it_data["lost"] else "⏳")
        item_text = f"{icon} Vuelta #{it_num} • {status} • {steps} pasos • Score {score} ({dur}s)"

        item = QListWidgetItem(item_text)
        item.setData(Qt.UserRole, it_data)
        self.iterations_list.addItem(item)

        # Seleccionar automáticamente la última iteración si es la primera o si el usuario no tiene otra activa
        if self.iterations_list.count() == 1:
            self.iterations_list.setCurrentRow(0)
            self._display_iteration(it_data)

    def _on_progress_updated(self, stats: dict) -> None:
        percent = int(stats.get("percent", 0))
        completed = stats.get("completed", 0)
        total = stats.get("total", 0)
        elapsed_s = stats.get("elapsed_s", 0)
        eta_s = stats.get("eta_s", 0)
        win_rate = stats.get("win_rate", 0.0)
        avg_steps = stats.get("avg_steps", 0)
        avg_score = stats.get("avg_score", 0.0)

        self.progress_bar.setValue(percent)
        self.progress_title_label.setText(f"PROGRESO GENERAL: {percent}% (Vuelta {completed} de {total})")

        m_el, s_el = divmod(int(elapsed_s), 60)
        m_eta, s_eta = divmod(int(eta_s), 60)
        self.time_label.setText(f"⏱ Transcurrido: {m_el:02d}:{s_el:02d} • Estimado (ETA): ~{m_eta:02d}:{s_eta:02d}")

        self.card_runs.value_label.setText(f"{completed} / {total}")  # type: ignore[attr-defined]
        self.card_win_rate.value_label.setText(f"{win_rate}%")         # type: ignore[attr-defined]
        self.card_avg_steps.value_label.setText(str(avg_steps))       # type: ignore[attr-defined]
        self.card_avg_score.value_label.setText(str(avg_score))       # type: ignore[attr-defined]

    def _on_test_finished(self, session_data: dict) -> None:
        self.current_worker = None
        self.refresh_saved_sessions_list()
        self.load_session_data(session_data, select_iteration_idx=0)

    def _on_test_error(self, err_msg: str) -> None:
        self.header_status_label.setText(f"Error en el test: {err_msg}")
        self.footer_status.setText(f"Error crítico: {err_msg}")
        self.cancel_button.setEnabled(False)

    def _on_cancel_clicked(self) -> None:
        if self.current_worker:
            self.current_worker.cancel()
            self.cancel_button.setText("DETENIENDO...")
            self.cancel_button.setEnabled(False)
            self.header_status_label.setText("Cancelando test a petición del usuario...")

    # ------------------ Selección y Visualización de Iteración ------------------
    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        it_data = item.data(Qt.UserRole)
        if it_data:
            self._display_iteration(it_data)

    def _display_iteration(self, it_data: dict) -> None:
        it_num = it_data.get("iteration", 1)
        status = it_data.get("status", "Completado")
        steps = it_data.get("steps", 0)
        max_steps = it_data.get("max_steps", 50)
        score = it_data.get("score", 0)
        max_score = it_data.get("max_score", 0)
        dur = it_data.get("duration", 0)
        rooms = it_data.get("rooms_discovered", 0)
        total_rooms = it_data.get("total_rooms", 0)

        badge_color = "#98c379" if it_data.get("won") else ("#e06c75" if it_data.get("lost") else "#e5c07b")

        # Información de fecha de cuándo ocurrió el testeo
        ts_fmt = ""
        if self.latest_session_data:
            ts_fmt = format_session_timestamp(self.latest_session_data.get("timestamp", ""))
        date_str = f" • Fecha del test: {ts_fmt}" if ts_fmt and ts_fmt != "Fecha desconocida" else ""

        self.transcript_info_label.setText(f"DETALLES DE LA PARTIDA #{it_num} • {status.upper()}")
        self.run_summary_banner.setText(
            f"Vuelta #{it_num}{date_str} • Estado: {status} • Pasos: {steps}/{max_steps} • "
            f"Score: {score}/{max_score if max_score else 1} • Salas: {rooms}/{total_rooms} • Tiempo: {dur}s"
        )
        self.run_summary_banner.setStyleSheet(
            f"background-color: #21252b; border: 1px solid {badge_color}; border-radius: 6px; padding: 8px 12px; color: #ffffff; font-weight: 600;"
        )

        # Renderizar burbujas de transcripción
        self._clear_transcript()
        transcript = it_data.get("transcript", [])
        for entry in transcript:
            role = entry.get("role", "agent")
            text = entry.get("text", "")
            bubble = TranscriptBubble(role, text, self.messages_container)
            self.messages_layout.insertWidget(self.messages_layout.count() - 1, bubble)

        QTimer.singleShot(50, self._scroll_transcript_bottom)

        # Emitir señal para sincronizar el mapa en LeftPanel
        self.iteration_selected.emit(it_data)

    def _clear_transcript(self) -> None:
        while self.messages_layout.count() > 1:
            item = self.messages_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()

    def _scroll_transcript_bottom(self) -> None:
        sb = self.scroll_area.verticalScrollBar()
        sb.setValue(sb.maximum())
