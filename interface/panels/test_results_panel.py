from __future__ import annotations

import os
from typing import Any, Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from controllers.test_controller import (
    format_session_timestamp,
    list_saved_test_sessions,
    load_test_session,
)
from interface.widgets.radar_chart import RadarChartWidget


class TestResultsPanel(QWidget):
    """Pantalla integral de resultados, métricas de TextWorld, análisis de desempeño,
    historial de pruebas guardadas y apartado para métricas del agente (tokens/latencia).
    """

    iteration_selected = Signal(dict)
    session_changed = Signal(dict)
    open_config_requested = Signal()
    open_test_requested = Signal()
    open_menu_requested = Signal()

    def __init__(
        self,
        on_open_config: Callable[[], None] | None = None,
        on_open_test: Callable[[], None] | None = None,
        on_open_menu: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("RightPanel")
        if on_open_config:
            self.open_config_requested.connect(on_open_config)
        if on_open_test:
            self.open_test_requested.connect(on_open_test)
        if on_open_menu:
            self.open_menu_requested.connect(on_open_menu)

        self.current_session: dict | None = None
        self.selected_iteration_idx: int = 0
        self._build_ui()
        self.refresh_saved_sessions_list()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(1, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Cabecera con selector de sesiones guardadas
        root_layout.addWidget(self._build_header())

        # 2. Área desplazable con todas las secciones de métricas y análisis
        scroll = QScrollArea(self)
        scroll.setObjectName("ConfigScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget(scroll)
        content.setObjectName("ConfigContentWidget")
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(25, 20, 25, 20)
        self.content_layout.setSpacing(18)

        # Sección 1: KPIs de Rendimiento en TextWorld
        self.content_layout.addWidget(self._build_textworld_metrics_section())

        # Sección 2: Apartado para Métricas del Agente (Tokens y Latencia)
        self.content_layout.addWidget(self._build_agent_metrics_section())

        # Sección 3: Tabla Detallada de Partidas
        self.content_layout.addWidget(self._build_iterations_table_section())

        scroll.setWidget(content)
        root_layout.addWidget(scroll, stretch=1)

        # 3. Barra inferior de navegación
        root_layout.addWidget(self._build_footer())

    def _build_header(self) -> QWidget:
        header = QWidget(self)
        header.setObjectName("ConfigHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(25, 14, 25, 14)

        title_box = QVBoxLayout()
        title_box.setSpacing(3)

        tag = QLabel("ANÁLISIS DE RENDIMIENTO & BENCHMARK", header)
        tag.setObjectName("ConfigHeaderTag")

        title = QLabel("Resultados y Diagnóstico del Agente", header)
        title.setObjectName("ConfigHeaderTitle")

        self.session_meta_label = QLabel("Sin sesión activa cargada", header)
        self.session_meta_label.setObjectName("ConfigHeaderSubtitle")

        title_box.addWidget(tag)
        title_box.addWidget(title)
        title_box.addWidget(self.session_meta_label)
        layout.addLayout(title_box)

        layout.addStretch()

        # Selector de sesiones guardadas
        history_box = QVBoxLayout()
        history_box.setSpacing(2)

        history_title = QLabel("HISTORIAL DE SESIONES", header)
        history_title.setStyleSheet("color: #abb2bf; font-size: 10px; font-weight: 700;")

        history_controls = QHBoxLayout()
        self.sessions_combo = QComboBox(header)
        self.sessions_combo.setObjectName("ConfigComboBox")
        self.sessions_combo.setMinimumWidth(220)
        self.sessions_combo.currentIndexChanged.connect(self._on_session_combo_changed)

        btn_reload = QPushButton("↻", header)
        btn_reload.setObjectName("HeaderControl")
        btn_reload.setToolTip("Recargar lista de sesiones guardadas")
        btn_reload.setCursor(Qt.PointingHandCursor)
        btn_reload.clicked.connect(self.refresh_saved_sessions_list)

        history_controls.addWidget(self.sessions_combo)
        history_controls.addWidget(btn_reload)

        history_box.addWidget(history_title)
        history_box.addLayout(history_controls)
        layout.addLayout(history_box)

        return header

    def _build_textworld_metrics_section(self) -> QWidget:
        container = QFrame(self)
        container.setObjectName("ConfigModeCard")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        header_layout = QHBoxLayout()
        lbl = QLabel("MÉTRICAS DE DESEMPEÑO EN EL JUEGO (TEXTWORLD)", container)
        lbl.setObjectName("ConfigSectionHeader")

        self.kpi_badge_eval = QLabel("PERFIL MULTIDIMENSIONAL DEL AGENTE", container)
        self.kpi_badge_eval.setStyleSheet(
            "background-color: rgba(97, 175, 239, 0.15); color: #59e8ff; "
            "border: 1px solid #59e8ff; border-radius: 4px; padding: 2px 8px; font-size: 10px; font-weight: 700;"
        )

        header_layout.addWidget(lbl)
        header_layout.addStretch()
        header_layout.addWidget(self.kpi_badge_eval)
        layout.addLayout(header_layout)

        # Contenedor dividido: Gráfico de Telaraña (Izquierda) + Tarjetas numéricas (Derecha)
        body_layout = QHBoxLayout()
        body_layout.setSpacing(18)

        # 1. Gráfico de Telaraña (Radar Chart)
        radar_box = QFrame(container)
        radar_box.setObjectName("TestRadarContainer")
        radar_layout = QVBoxLayout(radar_box)
        radar_layout.setContentsMargins(14, 12, 14, 12)
        radar_layout.setSpacing(6)

        radar_title_row = QHBoxLayout()
        radar_title = QLabel("🕸 DIAGRAMA DE TELARAÑA", radar_box)
        radar_title.setStyleSheet("color: #abb2bf; font-size: 11px; font-weight: 700; letter-spacing: 0.8px;")
        radar_scale_hint = QLabel("Escala 0% - 100% (Exterior = Mejor)", radar_box)
        radar_scale_hint.setStyleSheet("color: #59e8ff; font-size: 10px; font-weight: 600;")
        radar_title_row.addWidget(radar_title)
        radar_title_row.addStretch()
        radar_title_row.addWidget(radar_scale_hint)
        radar_layout.addLayout(radar_title_row)

        self.radar_chart = RadarChartWidget(radar_box)
        self.radar_chart.setMinimumSize(360, 310)
        radar_layout.addWidget(self.radar_chart)

        radar_footnote = QLabel(
            "💡 Eficiencia ajustada: Menos pasos tomados otorgan mayor puntaje hacia el exterior.",
            radar_box,
        )
        radar_footnote.setObjectName("ConfigHintLabel")
        radar_footnote.setAlignment(Qt.AlignCenter)
        radar_layout.addWidget(radar_footnote)

        body_layout.addWidget(radar_box, stretch=5)

        # 2. Grid de 4 tarjetas de métricas absolutas
        cards_widget = QWidget(container)
        cards_layout = QVBoxLayout(cards_widget)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(10)

        grid = QGridLayout()
        grid.setSpacing(10)

        # 1. Eficacia
        self.card_efficacy = self._create_metric_card(
            "EFICACIA (TASA DE VICTORIAS)",
            "0.0%",
            "#98c379",
            "Victorias: 0 • Derrotas: 0 • Límite: 0",
        )
        # 2. Eficiencia
        self.card_efficiency = self._create_metric_card(
            "EFICIENCIA EN PASOS",
            "--",
            "#59e8ff",
            "Mínimo: -- • Máximo: -- • Ratio: --",
        )
        # 3. Puntuación
        self.card_score = self._create_metric_card(
            "PUNTUACIÓN OBTENIDA",
            "--",
            "#e5c07b",
            "Promedio alcanzado vs Máximo posible",
        )
        # 4. Exploración
        self.card_exploration = self._create_metric_card(
            "EXPLORACIÓN ESPACIAL",
            "--",
            "#c678dd",
            "Salas descubiertas promedio por partida",
        )

        grid.addWidget(self.card_efficacy, 0, 0)
        grid.addWidget(self.card_efficiency, 0, 1)
        grid.addWidget(self.card_score, 1, 0)
        grid.addWidget(self.card_exploration, 1, 1)

        cards_layout.addLayout(grid)
        body_layout.addWidget(cards_widget, stretch=6)

        layout.addLayout(body_layout)
        return container

    def _create_metric_card(self, title: str, main_val: str, color: str, subtitle: str) -> QFrame:
        card = QFrame()
        card.setObjectName("TestMetricCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        t_lbl = QLabel(title)
        t_lbl.setObjectName("TestKpiTitle")

        v_lbl = QLabel(main_val)
        v_lbl.setObjectName("TestMetricMainValue")
        v_lbl.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: 800;")

        s_lbl = QLabel(subtitle)
        s_lbl.setObjectName("TestMetricSubtitle")
        s_lbl.setStyleSheet("color: #abb2bf; font-size: 11px;")

        layout.addWidget(t_lbl)
        layout.addWidget(v_lbl)
        layout.addWidget(s_lbl)

        card.v_lbl = v_lbl  # type: ignore[attr-defined]
        card.s_lbl = s_lbl  # type: ignore[attr-defined]
        return card

    def _build_agent_metrics_section(self) -> QWidget:
        container = QFrame(self)
        container.setObjectName("ConfigGymCard")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        lbl = QLabel("MÉTRICAS DE RECURSOS DEL AGENTE (TOKENS & INFERENCIA)", container)
        lbl.setObjectName("ConfigSectionHeader")

        badge = QLabel("PRÓXIMAMENTE / MODULAR", container)
        badge.setStyleSheet(
            "background-color: rgba(229, 192, 123, 0.15); color: #e5c07b; "
            "border: 1px solid #e5c07b; border-radius: 4px; padding: 2px 8px; font-size: 10px; font-weight: 700;"
        )

        header_layout.addWidget(lbl)
        header_layout.addStretch()
        header_layout.addWidget(badge)
        layout.addLayout(header_layout)

        desc = QLabel(
            "Apartado preparado para registrar el gasto de computación del modelo cuando se integre un LLM: "
            "tokens consumidos, latencia media por decisión y estimación de costos.",
            container,
        )
        desc.setObjectName("ConfigHintLabel")
        layout.addWidget(desc)

        grid = QGridLayout()
        grid.setSpacing(12)

        self.card_prompt_tokens = self._create_metric_card(
            "TOKENS DE ENTRADA (PROMPT)",
            "--",
            "#5c6370",
            "Tokens enviados en observaciones y contexto",
        )
        self.card_completion_tokens = self._create_metric_card(
            "TOKENS DE SALIDA (COMPLETION)",
            "--",
            "#5c6370",
            "Tokens generados en respuestas del agente",
        )
        self.card_latency = self._create_metric_card(
            "LATENCIA MEDIA POR ACCIÓN",
            "-- ms",
            "#5c6370",
            "Tiempo de respuesta del agente por paso",
        )
        self.card_cost = self._create_metric_card(
            "LLAMADAS API / COSTO ESTIMADO",
            "-- / $0.00",
            "#5c6370",
            "Llamadas totales y costo estimado de inferencia",
        )

        grid.addWidget(self.card_prompt_tokens, 0, 0)
        grid.addWidget(self.card_completion_tokens, 0, 1)
        grid.addWidget(self.card_latency, 1, 0)
        grid.addWidget(self.card_cost, 1, 1)

        layout.addLayout(grid)
        return container

    def _build_iterations_table_section(self) -> QWidget:
        container = QFrame(self)
        container.setObjectName("ConfigFileCard")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        lbl = QLabel("DESGLOSE DETALLADO DE PARTIDAS", container)
        lbl.setObjectName("ConfigSectionHeader")

        header_layout.addWidget(lbl)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        self.table = QTableWidget(container)
        self.table.setObjectName("TestResultsTable")
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Vuelta", "Resultado", "Pasos", "Puntuación", "Salas", "Tiempo"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.cellClicked.connect(self._on_table_cell_clicked)

        layout.addWidget(self.table)
        return container

    def _on_table_cell_clicked(self, row: int, col: int) -> None:
        self.selected_iteration_idx = row
        if self.current_session and "iterations" in self.current_session:
            its = self.current_session["iterations"]
            if 0 <= row < len(its):
                self.iteration_selected.emit(its[row])

    def _build_footer(self) -> QWidget:
        footer = QWidget(self)
        footer.setObjectName("ConfigActionBar")
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(25, 14, 25, 14)
        layout.setSpacing(15)

        self.footer_info = QLabel("Resultados listos para análisis", footer)
        self.footer_info.setObjectName("ConfigStatusLabel")
        layout.addWidget(self.footer_info, stretch=1)

        self.btn_back_menu = QPushButton("🏠 MENÚ", footer)
        self.btn_back_menu.setObjectName("HeaderControl")
        self.btn_back_menu.setCursor(Qt.PointingHandCursor)
        self.btn_back_menu.clicked.connect(self.open_menu_requested.emit)

        self.btn_back_test = QPushButton("PANTALLA DE TESTEO", footer)
        self.btn_back_test.setObjectName("HeaderControl")
        self.btn_back_test.setCursor(Qt.PointingHandCursor)
        self.btn_back_test.clicked.connect(self.open_test_requested.emit)

        self.btn_new_config = QPushButton("NUEVA CONFIGURACIÓN", footer)
        self.btn_new_config.setObjectName("ConfigStartButton")
        self.btn_new_config.setCursor(Qt.PointingHandCursor)
        self.btn_new_config.clicked.connect(self.open_config_requested.emit)

        layout.addWidget(self.btn_back_menu)
        layout.addWidget(self.btn_back_test)
        layout.addWidget(self.btn_new_config)
        return footer

    # ------------------ Gestión de Sesiones y Datos ------------------
    def refresh_saved_sessions_list(self) -> None:
        """Carga y actualiza el desplegable con las sesiones disponibles en disco."""
        self.sessions_combo.blockSignals(True)
        self.sessions_combo.clear()

        sessions = list_saved_test_sessions()
        for s in sessions:
            label = f"📅 {s['formatted_timestamp']} • {s['total_runs']} vueltas ({s['win_rate']}%)"
            self.sessions_combo.addItem(label, s["filepath"])

        self.sessions_combo.blockSignals(False)

        # Si hay sesiones y no hay una cargada, cargar la más reciente
        if sessions and self.current_session is None:
            self.load_session_from_file(sessions[0]["filepath"])

    def _on_session_combo_changed(self, idx: int) -> None:
        if idx >= 0:
            filepath = self.sessions_combo.itemData(idx)
            if filepath and os.path.exists(filepath):
                self.load_session_from_file(filepath)

    def load_session_from_file(self, filepath: str) -> None:
        try:
            data = load_test_session(filepath)
            self.set_session_data(data)
            self.session_changed.emit(data)
        except Exception as exc:
            self.footer_info.setText(f"Error cargando sesión: {exc}")

    def set_session_data(self, session_data: dict) -> None:
        """Carga y renderiza los datos completos de una sesión de test."""
        self.current_session = session_data
        summary = session_data.get("summary", {})
        its = session_data.get("iterations", [])
        mode = session_data.get("mode", "desconocido")
        ts = session_data.get("timestamp", "")
        formatted_ts = format_session_timestamp(ts)

        # Metadatos en cabecera
        total_runs = summary.get("total_runs", len(its))
        dur_s = summary.get("total_duration_s", 0)
        self.session_meta_label.setText(
            f"📅 Fecha de Ejecución: {formatted_ts} • Modo: {mode.upper()} • {total_runs} partidas evaluadas • Duración: {dur_s}s"
        )

        # Sincronizar desplegable sin bucles
        saved_fp = session_data.get("saved_filepath", "")
        self.sessions_combo.blockSignals(True)
        for i in range(self.sessions_combo.count()):
            if self.sessions_combo.itemData(i) == saved_fp:
                self.sessions_combo.setCurrentIndex(i)
                break
        self.sessions_combo.blockSignals(False)

        # Actualizar KPIs TextWorld
        win_rate = summary.get("win_rate_percent", 0.0)
        wins = summary.get("wins", 0)
        losses = summary.get("losses", 0)
        timeouts = summary.get("timeouts", 0)
        self.card_efficacy.v_lbl.setText(f"{win_rate}%")  # type: ignore[attr-defined]
        self.card_efficacy.s_lbl.setText(f"Victorias: {wins} • Derrotas: {losses} • Timeouts: {timeouts}")  # type: ignore[attr-defined]

        avg_steps = summary.get("avg_steps", 0.0)
        min_steps = summary.get("min_steps", 0)
        max_steps = summary.get("max_steps", 0)
        eff_ratio = summary.get("efficiency_ratio", 0.0)
        self.card_efficiency.v_lbl.setText(f"{avg_steps} pasos")  # type: ignore[attr-defined]
        self.card_efficiency.s_lbl.setText(f"Mejor: {min_steps} • Peor: {max_steps} • Eficiencia: {eff_ratio}")  # type: ignore[attr-defined]

        avg_score = summary.get("avg_score", 0.0)
        max_score = summary.get("max_score_achieved", 0)
        self.card_score.v_lbl.setText(f"{avg_score}")  # type: ignore[attr-defined]
        self.card_score.s_lbl.setText(f"Puntaje promedio • Máximo alcanzado: {max_score}")  # type: ignore[attr-defined]

        avg_rooms = summary.get("avg_rooms_discovered", 0.0)
        self.card_exploration.v_lbl.setText(f"{avg_rooms} salas")  # type: ignore[attr-defined]
        self.card_exploration.s_lbl.setText("Promedio de habitaciones descubiertas")  # type: ignore[attr-defined]

        # ----------------- Gráfico de Telaraña (Normalización y Métricas Invertidas) -----------------
        # 1. Eficacia: Tasa de victorias directa (0% - 100%)
        score_efficacy = float(win_rate)

        # 2. Eficiencia en Pasos: Invertida (Menos pasos = puntaje superior hacia el exterior)
        limit_steps = 50
        if its:
            limit_steps = max((it.get("max_steps", 50) for it in its), default=50)
        limit_steps = max(limit_steps, max_steps, 10)

        if avg_steps <= 0:
            score_efficiency = 0.0 if not its else 100.0
        else:
            step_ratio = (avg_steps - 1.0) / max(1.0, float(limit_steps - 1))
            score_efficiency = round(max(0.0, min(100.0, 100.0 * (1.0 - step_ratio))), 1)

        # 3. Puntuación: Proporción sobre el puntaje máximo alcanzable
        possible_max_score = 0
        if its:
            possible_max_score = max((it.get("max_score", 0) for it in its), default=0)
        if possible_max_score <= 0:
            possible_max_score = summary.get("max_score_achieved", 0) or 1
        score_points = round(max(0.0, min(100.0, (avg_score / max(1.0, float(possible_max_score))) * 100.0)), 1)

        # 4. Exploración: Cobertura de salas sobre el total del mapa
        world_rooms = session_data.get("world_config", {}).get("nb_rooms", 0)
        if not world_rooms and its:
            world_rooms = max((it.get("total_rooms", 0) for it in its), default=0)
        world_rooms = max(1, world_rooms or 1)
        score_exploration = round(max(0.0, min(100.0, (avg_rooms / float(world_rooms)) * 100.0)), 1)

        # 5. Supervivencia / Consistencia: Resistencia a derrotas críticas y timeouts
        total_eval = total_runs or len(its) or 1
        survival_ratio = max(0.0, (total_eval - losses - (timeouts * 0.5)) / float(total_eval))
        score_survival = round(max(0.0, min(100.0, survival_ratio * 100.0)), 1)

        radar_axes = [
            {
                "label": "Eficacia",
                "name": "Eficacia",
                "score": score_efficacy,
                "value": score_efficacy,
                "display_text": f"{score_efficacy:.1f}%",
                "display": f"{score_efficacy:.1f}%",
                "color": "#98c379",
                "description": "Tasa de victorias",
            },
            {
                "label": "Eficiencia",
                "name": "Eficiencia",
                "score": score_efficiency,
                "value": score_efficiency,
                "display_text": f"{score_efficiency:.1f}% ({avg_steps:.1f} pasos)",
                "display": f"{score_efficiency:.1f}% ({avg_steps:.1f} pasos)",
                "color": "#59e8ff",
                "description": "Menor uso de pasos",
            },
            {
                "label": "Puntuación",
                "name": "Puntuación",
                "score": score_points,
                "value": score_points,
                "display_text": f"{score_points:.1f}% ({avg_score:.1f}/{possible_max_score})",
                "display": f"{score_points:.1f}% ({avg_score:.1f}/{possible_max_score})",
                "color": "#e5c07b",
                "description": "Puntos sobre el máximo",
            },
            {
                "label": "Exploración",
                "name": "Exploración",
                "score": score_exploration,
                "value": score_exploration,
                "display_text": f"{score_exploration:.1f}% ({avg_rooms:.1f}/{world_rooms})",
                "display": f"{score_exploration:.1f}% ({avg_rooms:.1f}/{world_rooms})",
                "color": "#c678dd",
                "description": "Salas descubiertas",
            },
            {
                "label": "Supervivencia",
                "name": "Supervivencia",
                "score": score_survival,
                "value": score_survival,
                "display_text": f"{score_survival:.1f}%",
                "display": f"{score_survival:.1f}%",
                "color": "#61afef",
                "description": "Consistencia de supervivencia",
            },
        ]
        self.radar_chart.set_data(radar_axes)

        overall_perf = (score_efficacy + score_efficiency + score_points + score_exploration + score_survival) / 5.0
        self.kpi_badge_eval.setText(f"RENDIMIENTO GLOBAL: {overall_perf:.1f}%")

        # Actualizar tabla de partidas
        self.table.setRowCount(len(its))
        for row_idx, it in enumerate(its):
            it_num = it.get("iteration", row_idx + 1)
            status = it.get("status", "Completado")
            steps = it.get("steps", 0)
            score = it.get("score", 0)
            rooms = f"{it.get('rooms_discovered', 0)}/{it.get('total_rooms', 0)}"
            duration = f"{it.get('duration', 0)}s"

            item_num = QTableWidgetItem(f"#{it_num}")
            item_num.setTextAlignment(Qt.AlignCenter)

            item_status = QTableWidgetItem(status)
            item_status.setTextAlignment(Qt.AlignCenter)
            if it.get("won"):
                item_status.setForeground(Qt.green)
            elif it.get("lost"):
                item_status.setForeground(Qt.red)
            else:
                item_status.setForeground(Qt.yellow)

            item_steps = QTableWidgetItem(str(steps))
            item_steps.setTextAlignment(Qt.AlignCenter)

            item_score = QTableWidgetItem(str(score))
            item_score.setTextAlignment(Qt.AlignCenter)

            item_rooms = QTableWidgetItem(rooms)
            item_rooms.setTextAlignment(Qt.AlignCenter)

            item_dur = QTableWidgetItem(duration)
            item_dur.setTextAlignment(Qt.AlignCenter)

            self.table.setItem(row_idx, 0, item_num)
            self.table.setItem(row_idx, 1, item_status)
            self.table.setItem(row_idx, 2, item_steps)
            self.table.setItem(row_idx, 3, item_score)
            self.table.setItem(row_idx, 4, item_rooms)
            self.table.setItem(row_idx, 5, item_dur)

        saved_path = session_data.get("saved_filepath", "")
        self.footer_info.setText(f"Sesión guardada en: {saved_path}")

