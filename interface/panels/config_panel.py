from __future__ import annotations

import os
import random
import re
import time
from typing import Callable

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from textworld import EnvInfos
import textworld.generator as tw_gen

from agente.config import AgentConfig
from agente.factory import get_available_agents


class GameGeneratorWorker(QThread):
    finished_success = Signal(str, int, object)  # game_path, max_steps, request_infos
    finished_error = Signal(str)

    def __init__(
        self,
        mode: str,
        config: dict,
        max_steps: int,
        request_infos: EnvInfos,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.mode = mode
        self.config = config
        self.max_steps = max_steps
        self.request_infos = request_infos

    def run(self) -> None:
        try:
            os.makedirs("tw", exist_ok=True)
            if self.mode == "custom":
                opts = tw_gen.GameOptions()
                opts.nb_rooms = self.config["nb_rooms"]
                opts.nb_objects = self.config["nb_objects"]
                opts.quest_length = self.config["quest_length"]
                opts.quest_breadth = self.config["quest_breadth"]
                opts.nb_parallel_quests = self.config["nb_parallel_quests"]

                opts.chaining.subquests = self.config.get("subquests", False)
                opts.chaining.independent_chains = self.config.get("independent_chains", False)

                opts.grammar.theme = self.config.get("theme", "house")
                opts.grammar.include_adj = self.config.get("include_adj", False)
                opts.grammar.blend_descriptions = self.config.get("blend_descriptions", False)
                opts.grammar.blend_instructions = self.config.get("blend_instructions", False)
                opts.grammar.only_last_action = self.config.get("only_last_action", False)
                # ambiguous_instructions es inviable en TextWorld (causa 'assert False, not tested')
                opts.grammar.ambiguous_instructions = False
                opts.grammar.allowed_variables_numbering = self.config.get("entity_numbering", False)

                if self.config.get("seed") is not None:
                    opts.seeds = int(self.config["seed"])

                output_path = os.path.abspath("tw/custom_world.z8")
                opts.path = output_path
                opts.force_recompile = True

                game = tw_gen.make_game(opts)
                compiled_path = tw_gen.compile_game(game, opts)
                self.finished_success.emit(compiled_path, self.max_steps, self.request_infos)

            elif self.mode == "challenge":
                import textworld.challenges as challenges
                ch_type = self.config.get("challenge_type", "tw-treasure_hunter")
                name, make_fn, _ = challenges.CHALLENGES[ch_type]

                opts = tw_gen.GameOptions()
                opts.path = os.path.abspath(f"tw/{ch_type}.z8")
                opts.force_recompile = True
                opts.grammar.only_last_action = self.config.get("only_last_action", False)
                if self.config.get("seed") is not None:
                    opts.seeds = int(self.config["seed"])

                settings = {}
                if ch_type in {"tw-treasure_hunter", "tw-coin_collector"}:
                    settings["level"] = int(self.config.get("level", 1))

                game = make_fn(settings, opts)
                compiled_path = tw_gen.compile_game(game, opts)
                self.finished_success.emit(compiled_path, self.max_steps, self.request_infos)

            elif self.mode == "file":
                game_path = self.config.get("file_path", "")
                if not os.path.exists(game_path):
                    self.finished_error.emit(f"El archivo no existe: {game_path}")
                    return
                self.finished_success.emit(game_path, self.max_steps, self.request_infos)

        except Exception as exc:
            self.finished_error.emit(str(exc))


class LLMQuickTestWorker(QThread):
    """Hilo secundario para comprobar la conectividad en vivo con el servidor 2x RTX 4090."""
    finished_result = Signal(bool, str, float)  # success, message, latency_ms

    def __init__(self, base_url: str, model: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.base_url = base_url
        self.model = model

    def run(self) -> None:
        t0 = time.time()
        try:
            from langchain_core.messages import HumanMessage
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(
                base_url=self.base_url,
                api_key="EMPTY",
                model=self.model,
                temperature=0.0,
                max_tokens=60,
                timeout=12.0,
                max_retries=1,
            )
            res = llm.invoke([HumanMessage(content="Responde solo: OK")])
            latency = (time.time() - t0) * 1000.0
            content = str(res.content).strip()
            cleaned = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
            resp_word = cleaned if cleaned else content
            if len(resp_word) > 25:
                resp_word = resp_word[:25] + "..."
            self.finished_result.emit(True, f"Conectado: {self.model} ({resp_word})", latency)
        except Exception as exc:
            latency = (time.time() - t0) * 1000.0
            err_msg = str(exc)
            if len(err_msg) > 75:
                err_msg = err_msg[:75] + "..."
            self.finished_result.emit(False, f"Error: {err_msg}", latency)


class ConfigPanel(QWidget):
    def __init__(
        self,
        on_start_game: Callable[..., None],
        on_start_test: Callable[..., None] | None = None,
        on_return_menu: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.on_start_game = on_start_game
        self.on_start_test = on_start_test
        self.on_return_menu = on_return_menu
        self.setObjectName("RightPanel")
        self.worker: GameGeneratorWorker | None = None
        self.base_agent_config = AgentConfig()
        self.llm_test_worker: LLMQuickTestWorker | None = None

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(1, 0, 0, 0)
        root_layout.setSpacing(0)

        # Header
        root_layout.addWidget(self._build_header())

        # Scrollable content area
        scroll_area = QScrollArea(self)
        scroll_area.setObjectName("ConfigScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content_widget = QWidget(scroll_area)
        content_widget.setObjectName("ConfigContentWidget")
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setContentsMargins(25, 20, 25, 20)
        self.content_layout.setSpacing(18)

        # Mode selector
        self._build_mode_selector()

        # Stacked pages for each mode
        self.mode_stack = QStackedWidget(content_widget)
        self.mode_stack.setObjectName("ConfigModeStack")

        self.custom_mode_widget = self._build_custom_options()
        self.file_mode_widget = self._build_file_options()
        self.challenge_mode_widget = self._build_challenge_options()

        self.mode_stack.addWidget(self.custom_mode_widget)     # Index 0
        self.mode_stack.addWidget(self.file_mode_widget)       # Index 1
        self.mode_stack.addWidget(self.challenge_mode_widget)  # Index 2

        self.content_layout.addWidget(self.mode_stack)

        # Execution / Gym common settings
        self.content_layout.addWidget(self._build_gym_options())

        # Agent architecture and memory settings
        self.content_layout.addWidget(self._build_agent_options())

        # Testing & Benchmark settings
        self.content_layout.addWidget(self._build_test_options())

        scroll_area.setWidget(content_widget)
        root_layout.addWidget(scroll_area, stretch=1)

        # Action bar at bottom
        root_layout.addWidget(self._build_action_bar())

        self._update_summary()

    def _build_header(self) -> QWidget:
        header = QWidget(self)
        header.setObjectName("ConfigHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(25, 16, 25, 16)

        title_box = QVBoxLayout()
        title_box.setSpacing(4)

        tag = QLabel("TEXTWORLD GENERATOR & CONFIG", header)
        tag.setObjectName("ConfigHeaderTag")

        title = QLabel("Configuración del Entorno", header)
        title.setObjectName("ConfigHeaderTitle")

        subtitle = QLabel("Personaliza las dimensiones del mundo, misiones, gramática y parámetros de ejecución.", header)
        subtitle.setObjectName("ConfigHeaderSubtitle")

        title_box.addWidget(tag)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        layout.addLayout(title_box)
        layout.addStretch()

        if self.on_return_menu:
            btn_menu = QPushButton("🏠 MENÚ", header)
            btn_menu.setObjectName("HeaderControl")
            btn_menu.setCursor(Qt.PointingHandCursor)
            btn_menu.clicked.connect(self.on_return_menu)
            layout.addWidget(btn_menu)

        return header

    def _build_mode_selector(self) -> None:
        container = QFrame(self)
        container.setObjectName("ConfigModeCard")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        label = QLabel("MODO DE JUEGO", container)
        label.setObjectName("ConfigSectionHeader")
        layout.addWidget(label)

        radios_layout = QHBoxLayout()
        radios_layout.setSpacing(15)

        self.mode_btn_group = QButtonGroup(self)

        self.radio_custom = QRadioButton("Mundo Personalizado", container)
        self.radio_custom.setChecked(True)
        self.radio_custom.setCursor(Qt.PointingHandCursor)
        self.radio_file = QRadioButton("Cargar Juego (.z8)", container)
        self.radio_file.setCursor(Qt.PointingHandCursor)
        self.radio_challenge = QRadioButton("Desafíos TextWorld", container)
        self.radio_challenge.setCursor(Qt.PointingHandCursor)

        self.mode_btn_group.addButton(self.radio_custom, 0)
        self.mode_btn_group.addButton(self.radio_file, 1)
        self.mode_btn_group.addButton(self.radio_challenge, 2)

        self.mode_btn_group.idClicked.connect(self._on_mode_changed)

        radios_layout.addWidget(self.radio_custom)
        radios_layout.addWidget(self.radio_file)
        radios_layout.addWidget(self.radio_challenge)
        radios_layout.addStretch()

        layout.addLayout(radios_layout)
        self.content_layout.addWidget(container)

    def _on_mode_changed(self, mode_id: int) -> None:
        self.mode_stack.setCurrentIndex(mode_id)
        # Si estamos en modo Archivo, la opción de "Mundo nuevo por vuelta" es incompatible
        if hasattr(self, "radio_var_diff"):
            if mode_id == 1:
                self.radio_var_diff.setEnabled(False)
                self.radio_var_diff.setChecked(False)
                self.radio_var_same.setChecked(True)
                self.radio_var_diff.setCursor(Qt.ForbiddenCursor)
                self.radio_var_diff.setToolTip("Incompatible con juegos precompilados (.z8): el mundo es estático y no usa semillas.")
                self._validate_file_path()
            else:
                self.radio_var_diff.setEnabled(True)
                self.radio_var_diff.setCursor(Qt.PointingHandCursor)
                self.radio_var_diff.setToolTip("")
                self.status_label.setStyleSheet("color: #59ff93; font-size: 11px;")
                self.status_label.setText("Listo para configurar")
                self.start_button.setEnabled(True)
                self.test_button.setEnabled(True)
                self.start_button.setCursor(Qt.PointingHandCursor)
                self.test_button.setCursor(Qt.PointingHandCursor)
        self._update_summary()

    # ------------------ Mode 1: Custom Options ------------------
    def _build_custom_options(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        tab_widget = QTabWidget(widget)
        tab_widget.setObjectName("ConfigTabWidget")

        # Tab 1: Mundo & Habitaciones
        tab_world = QWidget()
        world_layout = QVBoxLayout(tab_world)
        world_layout.setContentsMargins(16, 16, 16, 16)
        world_layout.setSpacing(16)

        # Rooms slider
        self.rooms_slider, self.rooms_val_lbl = self._create_slider_control(
            "Cantidad de Habitaciones:", min_val=1, max_val=15, default_val=4
        )
        self.rooms_slider.valueChanged.connect(self._update_summary)
        world_layout.addLayout(self._wrap_labeled_control("Habitaciones (World Size)", self.rooms_slider, self.rooms_val_lbl))

        # Objects slider
        self.objects_slider, self.objects_val_lbl = self._create_slider_control(
            "Cantidad de Objetos:", min_val=0, max_val=20, default_val=4
        )
        self.objects_slider.valueChanged.connect(self._update_summary)
        world_layout.addLayout(self._wrap_labeled_control("Objetos en el Mundo", self.objects_slider, self.objects_val_lbl))

        # Theme combo
        theme_row = QHBoxLayout()
        theme_lbl = QLabel("Tema Gramatical:")
        theme_lbl.setObjectName("ConfigOptionLabel")
        self.theme_combo = QComboBox()
        self.theme_combo.setObjectName("ConfigComboBox")
        self.theme_combo.addItem("Casa (House)", "house")
        self.theme_combo.addItem("Básico (Basic)", "basic")
        self.theme_combo.setCursor(Qt.PointingHandCursor)
        self.theme_combo.currentIndexChanged.connect(self._update_summary)
        theme_row.addWidget(theme_lbl)
        theme_row.addWidget(self.theme_combo)
        theme_row.addStretch()
        world_layout.addLayout(theme_row)
        world_layout.addStretch()

        tab_widget.addTab(tab_world, "🏰 Mundo")

        # Tab 2: Misiones & Quests
        tab_quest = QWidget()
        quest_layout = QVBoxLayout(tab_quest)
        quest_layout.setContentsMargins(16, 16, 16, 16)
        quest_layout.setSpacing(16)

        # Quest length
        self.quest_len_slider, self.quest_len_val_lbl = self._create_slider_control(
            "Pasos para Resolver (Quest Length):", min_val=1, max_val=12, default_val=3
        )
        self.quest_len_slider.valueChanged.connect(self._on_quest_len_changed)
        quest_layout.addLayout(self._wrap_labeled_control("Longitud de Misión", self.quest_len_slider, self.quest_len_val_lbl))

        # Quest breadth
        self.quest_breadth_slider, self.quest_breadth_val_lbl = self._create_slider_control(
            "Amplitud de Subquests (Breadth):", min_val=1, max_val=5, default_val=1
        )
        self.quest_breadth_slider.valueChanged.connect(self._on_quest_breadth_changed)
        breadth_box = self._wrap_labeled_control("Amplitud (Sub-misiones paralelas)", self.quest_breadth_slider, self.quest_breadth_val_lbl)
        
        self.breadth_hint_lbl = QLabel("")
        self.breadth_hint_lbl.setObjectName("ConfigWarningHint")
        self.breadth_hint_lbl.setVisible(False)
        breadth_box.addWidget(self.breadth_hint_lbl)
        quest_layout.addLayout(breadth_box)

        # Parallel quests spinbox
        parallel_row = QHBoxLayout()
        parallel_lbl = QLabel("Misiones Paralelas Independientes:")
        parallel_lbl.setObjectName("ConfigOptionLabel")
        self.parallel_spin = QSpinBox()
        self.parallel_spin.setRange(1, 4)
        self.parallel_spin.setValue(1)
        self.parallel_spin.setCursor(Qt.PointingHandCursor)
        self.parallel_spin.valueChanged.connect(self._update_summary)
        parallel_row.addWidget(parallel_lbl)
        parallel_row.addWidget(self.parallel_spin)
        parallel_row.addStretch()
        quest_layout.addLayout(parallel_row)

        # Advanced quest toggles
        adv_group = QGroupBox("Opciones Avanzadas de Chaining")
        adv_layout = QVBoxLayout(adv_group)
        self.chk_subquests = QCheckBox("Permitir submisiones incompletas (subquests abiertas)")
        self.chk_subquests.setCursor(Qt.PointingHandCursor)
        self.chk_independent = QCheckBox("Permitir cadenas de quests totalmente independientes")
        self.chk_independent.setCursor(Qt.PointingHandCursor)
        adv_layout.addWidget(self.chk_subquests)
        adv_layout.addWidget(self.chk_independent)
        quest_layout.addWidget(adv_group)

        # Opciones de Pistas / Guía del Objetivo (only_last_action)
        hints_group = QGroupBox("Guía y Pistas del Objetivo (TextWorld)")
        hints_layout = QVBoxLayout(hints_group)
        hints_layout.setSpacing(6)

        self.chk_only_last = QCheckBox("Deshabilitar pistas paso a paso del objetivo (only_last_action)")
        self.chk_only_last.setChecked(True)
        self.chk_only_last.setCursor(Qt.PointingHandCursor)
        self.chk_only_last.toggled.connect(self._on_only_last_toggled)

        hint_only_last = QLabel(
            "💡 Al marcar esta opción (only_last_action=True), TextWorld NO revelará el walkthrough "
            "paso a paso ni dará pistas intermedias en el objetivo; solo indicará la meta final (ej. 'Recupera la escoba')."
        )
        hint_only_last.setObjectName("ConfigHintLabel")
        hint_only_last.setWordWrap(True)

        hints_layout.addWidget(self.chk_only_last)
        hints_layout.addWidget(hint_only_last)
        quest_layout.addWidget(hints_group)
        quest_layout.addStretch()

        tab_widget.addTab(tab_quest, "🎯 Misión")

        # Tab 3: Lenguaje y Gramática
        tab_grammar = QWidget()
        grammar_layout = QVBoxLayout(tab_grammar)
        grammar_layout.setContentsMargins(16, 16, 16, 16)
        grammar_layout.setSpacing(12)

        self.chk_include_adj = QCheckBox("Incluir adjetivos en nombres de entidades (ej. red apple)")
        self.chk_include_adj.setChecked(True)
        self.chk_include_adj.setCursor(Qt.PointingHandCursor)

        self.chk_blend_desc = QCheckBox("Fusionar descripciones entre oraciones consecutivas")
        self.chk_blend_desc.setChecked(True)
        self.chk_blend_desc.setCursor(Qt.PointingHandCursor)

        self.chk_blend_inst = QCheckBox("Fusionar instrucciones consecutivas en una sola frase")
        self.chk_blend_inst.setCursor(Qt.PointingHandCursor)

        self.chk_only_last_grammar = QCheckBox("Deshabilitar pistas paso a paso del objetivo (only_last_action)")
        self.chk_only_last_grammar.setChecked(True)
        self.chk_only_last_grammar.setCursor(Qt.PointingHandCursor)
        self.chk_only_last_grammar.toggled.connect(self._on_grammar_only_last_toggled)

        # Instrucciones ambiguas: inviable en TextWorld (assert False, "not tested")
        ambig_row = QHBoxLayout()
        ambig_row.setSpacing(8)
        self.chk_ambiguous = QCheckBox("Instrucciones ambiguas usando tipos de objetos (ej. container)")
        self.chk_ambiguous.setChecked(False)
        self.chk_ambiguous.setEnabled(False)
        self.chk_ambiguous.setCursor(Qt.ForbiddenCursor)
        self.chk_ambiguous.setToolTip("Inviable: Genera un fallo fatal 'AssertionError: not tested' en el motor de TextWorld.")

        ambig_badge = QLabel("⚠️ NO DISPONIBLE")
        ambig_badge.setObjectName("ConfigLockedBadgeAlert")
        ambig_badge.setToolTip("Función no implementada en TextWorld (inviable).")

        ambig_row.addWidget(self.chk_ambiguous)
        ambig_row.addWidget(ambig_badge)
        ambig_row.addStretch()

        self.chk_numbering = QCheckBox("Numerar entidades duplicadas (ej. 'key 1', 'key 2')")
        self.chk_numbering.setChecked(True)
        self.chk_numbering.setCursor(Qt.PointingHandCursor)

        grammar_layout.addWidget(self.chk_include_adj)
        grammar_layout.addWidget(self.chk_blend_desc)
        grammar_layout.addWidget(self.chk_blend_inst)
        grammar_layout.addWidget(self.chk_only_last_grammar)
        grammar_layout.addLayout(ambig_row)
        grammar_layout.addWidget(self.chk_numbering)
        grammar_layout.addStretch()

        tab_widget.addTab(tab_grammar, "📝 Gramática")

        # Tab 4: Semilla de Aleatoriedad
        tab_seed = QWidget()
        seed_layout = QVBoxLayout(tab_seed)
        seed_layout.setContentsMargins(16, 16, 16, 16)
        seed_layout.setSpacing(14)

        self.chk_random_seed = QCheckBox("Generar con Semilla Aleatoria en cada partida")
        self.chk_random_seed.setChecked(True)
        self.chk_random_seed.setCursor(Qt.PointingHandCursor)
        self.chk_random_seed.toggled.connect(self._on_random_seed_toggled)

        seed_input_row = QHBoxLayout()
        seed_lbl = QLabel("Semilla Fija (Reproducible):")
        seed_lbl.setObjectName("ConfigOptionLabel")
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(0, 999999)
        self.seed_spin.setValue(42)
        self.seed_spin.setEnabled(False)
        self.seed_spin.setCursor(Qt.ForbiddenCursor)

        seed_input_row.addWidget(seed_lbl)
        seed_input_row.addWidget(self.seed_spin)
        seed_input_row.addStretch()

        seed_layout.addWidget(self.chk_random_seed)
        seed_layout.addLayout(seed_input_row)

        seed_hint = QLabel("Una semilla fija permite generar exactamente la misma distribución de cuartos, objetos y acertijos.")
        seed_hint.setObjectName("ConfigHintLabel")
        seed_hint.setWordWrap(True)
        seed_layout.addWidget(seed_hint)
        seed_layout.addStretch()

        tab_widget.addTab(tab_seed, "🎲 Semilla")

        layout.addWidget(tab_widget)
        return widget

    def _on_quest_len_changed(self, new_len: int) -> None:
        if new_len <= 2:
            self.quest_breadth_slider.setValue(1)
            self.quest_breadth_slider.setEnabled(False)
            self.quest_breadth_slider.setCursor(Qt.ForbiddenCursor)
            self.breadth_hint_lbl.setText("🔒 Bloqueado: Ramificar subquests requiere al menos 3 pasos de longitud de misión.")
            self.breadth_hint_lbl.setVisible(True)
        else:
            self.quest_breadth_slider.setEnabled(True)
            self.quest_breadth_slider.setCursor(Qt.PointingHandCursor)
            max_b = min(5, max(1, new_len - 1))
            self.quest_breadth_slider.setMaximum(max_b)
            if self.quest_breadth_slider.value() > max_b:
                self.quest_breadth_slider.setValue(max_b)
            if max_b < 5:
                self.breadth_hint_lbl.setText(f"ℹ️ Amplitud máxima permitida para longitud {new_len}: {max_b}")
                self.breadth_hint_lbl.setVisible(True)
            else:
                self.breadth_hint_lbl.setVisible(False)
        self._update_summary()

    def _on_quest_breadth_changed(self, new_breadth: int) -> None:
        if new_breadth > 1:
            self.chk_subquests.setChecked(True)
            self.chk_subquests.setEnabled(False)
            self.chk_subquests.setCursor(Qt.ForbiddenCursor)
            self.chk_subquests.setToolTip("Bloqueado activo: Requerido obligatoriamente por TextWorld cuando la amplitud es > 1.")
        else:
            self.chk_subquests.setEnabled(True)
            self.chk_subquests.setCursor(Qt.PointingHandCursor)
            self.chk_subquests.setToolTip("")
        self._update_summary()

    def _on_only_last_toggled(self, checked: bool) -> None:
        if hasattr(self, "chk_only_last_grammar") and self.chk_only_last_grammar.isChecked() != checked:
            self.chk_only_last_grammar.blockSignals(True)
            self.chk_only_last_grammar.setChecked(checked)
            self.chk_only_last_grammar.blockSignals(False)

        if checked:
            self.chk_blend_inst.setChecked(False)
            self.chk_blend_inst.setEnabled(False)
            self.chk_blend_inst.setCursor(Qt.ForbiddenCursor)
            self.chk_blend_inst.setToolTip("Incompatible: No se pueden fusionar instrucciones si solo se describe la última acción.")
        else:
            self.chk_blend_inst.setEnabled(True)
            self.chk_blend_inst.setCursor(Qt.PointingHandCursor)
            self.chk_blend_inst.setToolTip("")
        self._update_summary()

    def _on_grammar_only_last_toggled(self, checked: bool) -> None:
        if hasattr(self, "chk_only_last") and self.chk_only_last.isChecked() != checked:
            self.chk_only_last.setChecked(checked)

    def _on_challenge_only_last_toggled(self, checked: bool) -> None:
        self._update_summary()

    def _on_random_seed_toggled(self, checked: bool) -> None:
        self.seed_spin.setEnabled(not checked)
        self.seed_spin.setCursor(Qt.PointingHandCursor if not checked else Qt.ForbiddenCursor)

    # ------------------ Mode 2: Existing File Options ------------------
    def _build_file_options(self) -> QWidget:
        widget = QFrame()
        widget.setObjectName("ConfigFileCard")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        label = QLabel("SELECCIONAR ARCHIVO DE JUEGO (.z8)", widget)
        label.setObjectName("ConfigSectionHeader")
        layout.addWidget(label)

        # Predefined games in project
        predefined_row = QHBoxLayout()
        predefined_lbl = QLabel("Juegos del Proyecto:")
        predefined_lbl.setObjectName("ConfigOptionLabel")
        self.file_combo = QComboBox()
        self.file_combo.setObjectName("ConfigComboBox")
        self.file_combo.setCursor(Qt.PointingHandCursor)

        # Discover project z8 files
        project_games = [
            ("Mundo C (tw/mundo-c.z8)", "tw/mundo-c.z8"),
            ("Mundo Original (tw/mundo.z8)", "tw/mundo.z8"),
            ("Simple Game (text-world/simple_game.z8)", "text-world/simple_game.z8"),
        ]
        for name, path in project_games:
            if os.path.exists(path):
                self.file_combo.addItem(name, path)

        self.file_combo.currentIndexChanged.connect(self._on_predefined_file_selected)
        predefined_row.addWidget(predefined_lbl)
        predefined_row.addWidget(self.file_combo, stretch=1)
        layout.addLayout(predefined_row)

        # Custom path row
        path_row = QHBoxLayout()
        path_lbl = QLabel("Ruta del Archivo:")
        path_lbl.setObjectName("ConfigOptionLabel")
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setObjectName("ConfigPathEdit")
        if self.file_combo.count() > 0:
            self.file_path_edit.setText(self.file_combo.currentData())
        self.file_path_edit.textChanged.connect(self._validate_file_path)

        browse_btn = QPushButton("Examinar...")
        browse_btn.setObjectName("ConfigBrowseButton")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.clicked.connect(self._browse_game_file)

        path_row.addWidget(path_lbl)
        path_row.addWidget(self.file_path_edit, stretch=1)
        path_row.addWidget(browse_btn)
        layout.addLayout(path_row)

        hint = QLabel("Puedes cargar mundos ya compilados (.z8) creados previamente o distribuidos para TextWorld.")
        hint.setObjectName("ConfigHintLabel")
        layout.addWidget(hint)
        layout.addStretch()

        return widget

    def _validate_file_path(self) -> bool:
        mode_id = self.mode_btn_group.checkedId()
        if mode_id != 1:  # No estamos en modo archivo
            return True
        path = self.file_path_edit.text().strip()
        if not path or not os.path.exists(path):
            self.status_label.setStyleSheet("color: #e06c75; font-size: 11px;")
            self.status_label.setText("⚠️ Por favor selecciona un archivo .z8 / .json válido existente.")
            self.start_button.setEnabled(False)
            self.test_button.setEnabled(False)
            self.start_button.setCursor(Qt.ForbiddenCursor)
            self.test_button.setCursor(Qt.ForbiddenCursor)
            return False
        else:
            self.status_label.setStyleSheet("color: #59ff93; font-size: 11px;")
            self.status_label.setText("Listo para configurar")
            self.start_button.setEnabled(True)
            self.test_button.setEnabled(True)
            self.start_button.setCursor(Qt.PointingHandCursor)
            self.test_button.setCursor(Qt.PointingHandCursor)
            return True

    def _on_predefined_file_selected(self, index: int) -> None:
        path = self.file_combo.itemData(index)
        if path:
            self.file_path_edit.setText(path)
            self._validate_file_path()
            self._update_summary()

    def _browse_game_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Juego TextWorld",
            os.getcwd(),
            "Juegos TextWorld (*.z8 *.json);;Todos los archivos (*)",
        )
        if file_path:
            self.file_path_edit.setText(file_path)
            self._validate_file_path()
            self._update_summary()

    # ------------------ Mode 3: Challenges ------------------
    def _build_challenge_options(self) -> QWidget:
        widget = QFrame()
        widget.setObjectName("ConfigChallengeCard")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(14)

        label = QLabel("DESAFÍOS ESPECIALES TEXTWORLD", widget)
        label.setObjectName("ConfigSectionHeader")
        layout.addWidget(label)

        challenge_row = QHBoxLayout()
        challenge_lbl = QLabel("Tipo de Desafío:")
        challenge_lbl.setObjectName("ConfigOptionLabel")
        self.challenge_combo = QComboBox()
        self.challenge_combo.setObjectName("ConfigComboBox")
        self.challenge_combo.addItem("Treasure Hunter (Caza del Tesoro)", "tw-treasure_hunter")
        self.challenge_combo.addItem("Coin Collector (Recolector de Monedas)", "tw-coin_collector")
        self.challenge_combo.setCursor(Qt.PointingHandCursor)
        self.challenge_combo.currentIndexChanged.connect(self._update_summary)

        challenge_row.addWidget(challenge_lbl)
        challenge_row.addWidget(self.challenge_combo, stretch=1)
        layout.addLayout(challenge_row)

        self.difficulty_slider, self.difficulty_val_lbl = self._create_slider_control(
            "Nivel de Dificultad (Level):", min_val=1, max_val=30, default_val=1
        )
        layout.addLayout(self._wrap_labeled_control("Dificultad (1-30)", self.difficulty_slider, self.difficulty_val_lbl))

        # Semilla específica para el modo Desafío
        seed_group = QGroupBox("Semilla del Desafío")
        seed_layout = QVBoxLayout(seed_group)
        self.chk_challenge_random_seed = QCheckBox("Generar con Semilla Aleatoria")
        self.chk_challenge_random_seed.setChecked(True)
        self.chk_challenge_random_seed.setCursor(Qt.PointingHandCursor)
        self.chk_challenge_random_seed.toggled.connect(self._on_challenge_seed_toggled)

        ch_seed_row = QHBoxLayout()
        ch_seed_lbl = QLabel("Semilla Fija:")
        ch_seed_lbl.setObjectName("ConfigOptionLabel")
        self.challenge_seed_spin = QSpinBox()
        self.challenge_seed_spin.setRange(0, 999999)
        self.challenge_seed_spin.setValue(42)
        self.challenge_seed_spin.setEnabled(False)
        self.challenge_seed_spin.setCursor(Qt.ForbiddenCursor)

        ch_seed_row.addWidget(ch_seed_lbl)
        ch_seed_row.addWidget(self.challenge_seed_spin)
        ch_seed_row.addStretch()

        seed_layout.addWidget(self.chk_challenge_random_seed)
        seed_layout.addLayout(ch_seed_row)
        layout.addWidget(seed_group)

        # Guía y Pistas del Desafío (only_last_action)
        ch_hints_group = QGroupBox("Guía y Pistas del Objetivo (TextWorld)")
        ch_hints_layout = QVBoxLayout(ch_hints_group)
        ch_hints_layout.setSpacing(6)
        self.chk_challenge_only_last = QCheckBox("Deshabilitar pistas paso a paso del objetivo (only_last_action)")
        self.chk_challenge_only_last.setChecked(True)
        self.chk_challenge_only_last.setCursor(Qt.PointingHandCursor)
        self.chk_challenge_only_last.toggled.connect(self._on_challenge_only_last_toggled)

        ch_hint_lbl = QLabel(
            "💡 Al marcar esta opción (only_last_action=True), TextWorld solo describe la meta final "
            "sin revelar los pasos intermedios de navegación ni el walkthrough."
        )
        ch_hint_lbl.setObjectName("ConfigHintLabel")
        ch_hint_lbl.setWordWrap(True)
        ch_hints_layout.addWidget(self.chk_challenge_only_last)
        ch_hints_layout.addWidget(ch_hint_lbl)
        layout.addWidget(ch_hints_group)

        hint = QLabel("Los desafíos TextWorld generan problemas estandarizados con misiones graduadas en complejidad.")
        hint.setObjectName("ConfigHintLabel")
        layout.addWidget(hint)
        layout.addStretch()

        return widget

    def _on_challenge_seed_toggled(self, checked: bool) -> None:
        self.challenge_seed_spin.setEnabled(not checked)
        self.challenge_seed_spin.setCursor(Qt.PointingHandCursor if not checked else Qt.ForbiddenCursor)

    # ------------------ Common Gym Options ------------------
    def _build_gym_options(self) -> QWidget:
        container = QFrame(self)
        container.setObjectName("ConfigGymCard")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QLabel("PARÁMETROS DEL ENTORNO GYM", container)
        header.setObjectName("ConfigSectionHeader")
        layout.addWidget(header)

        # Max episode steps slider
        self.max_steps_slider, self.max_steps_val_lbl = self._create_slider_control(
            "Pasos Máximos por Episodio:", min_val=10, max_val=150, default_val=50
        )
        self.max_steps_slider.valueChanged.connect(self._update_summary)
        layout.addLayout(self._wrap_labeled_control("Pasos Máximos (Max Episode Steps)", self.max_steps_slider, self.max_steps_val_lbl))

        # EnvInfos Checkboxes
        infos_group = QGroupBox("Información Solicitada al Entorno (EnvInfos)")
        infos_layout = QGridLayout(infos_group)
        infos_layout.setSpacing(10)

        # 1. Localización (Requerido)
        loc_box = QHBoxLayout()
        loc_box.setSpacing(6)
        self.chk_location = QCheckBox("Localización (location)")
        self.chk_location.setChecked(True)
        self.chk_location.setEnabled(False)  # Requerido por el mapa
        self.chk_location.setCursor(Qt.ForbiddenCursor)
        self.chk_location.setToolTip("Dato obligatorio: requerido para la navegación y actualización del mapa.")
        badge_loc = QLabel("🔒 REQUERIDO")
        badge_loc.setObjectName("ConfigLockedBadge")
        badge_loc.setToolTip("Requerido para el funcionamiento del mapa interactivo.")
        loc_box.addWidget(self.chk_location)
        loc_box.addWidget(badge_loc)
        loc_box.addStretch()

        # 2. Hechos del Mundo (Requerido)
        facts_box = QHBoxLayout()
        facts_box.setSpacing(6)
        self.chk_facts = QCheckBox("Hechos del Mundo (facts)")
        self.chk_facts.setChecked(True)
        self.chk_facts.setEnabled(False)     # Requerido por el mapa
        self.chk_facts.setCursor(Qt.ForbiddenCursor)
        self.chk_facts.setToolTip("Dato obligatorio: el grafo y el estado del mundo dependen de los hechos.")
        badge_facts = QLabel("🔒 REQUERIDO")
        badge_facts.setObjectName("ConfigLockedBadge")
        badge_facts.setToolTip("Requerido para procesar las entidades y salas.")
        facts_box.addWidget(self.chk_facts)
        facts_box.addWidget(badge_facts)
        facts_box.addStretch()

        # 3. Comandos Admisibles (Requerido)
        cmds_box = QHBoxLayout()
        cmds_box.setSpacing(6)
        self.chk_commands = QCheckBox("Comandos Admisibles (admissible_commands)")
        self.chk_commands.setChecked(True)
        self.chk_commands.setEnabled(False)  # Requerido por el agente
        self.chk_commands.setCursor(Qt.ForbiddenCursor)
        self.chk_commands.setToolTip("Dato obligatorio: imprescindible para que el agente autónomo seleccione acciones válidas.")
        badge_cmds = QLabel("🔒 REQUERIDO")
        badge_cmds.setObjectName("ConfigLockedBadge")
        badge_cmds.setToolTip("Requerido por la IA para conocer las acciones válidas en cada turno.")
        cmds_box.addWidget(self.chk_commands)
        cmds_box.addWidget(badge_cmds)
        cmds_box.addStretch()

        # 4. Descripción
        self.chk_description = QCheckBox("Descripción de sala (description)")
        self.chk_description.setChecked(True)
        self.chk_description.setCursor(Qt.PointingHandCursor)

        # 5. Inventario
        self.chk_inventory = QCheckBox("Inventario (inventory)")
        self.chk_inventory.setChecked(True)
        self.chk_inventory.setCursor(Qt.PointingHandCursor)

        # 6. Score
        self.chk_score = QCheckBox("Puntuación (score)")
        self.chk_score.setChecked(True)
        self.chk_score.setCursor(Qt.PointingHandCursor)

        # 7. Won/lost
        self.chk_won_lost = QCheckBox("Victoria / Derrota (won / lost)")
        self.chk_won_lost.setChecked(True)
        self.chk_won_lost.setCursor(Qt.PointingHandCursor)

        infos_layout.addLayout(loc_box, 0, 0)
        infos_layout.addLayout(facts_box, 0, 1)
        infos_layout.addLayout(cmds_box, 1, 0)
        infos_layout.addWidget(self.chk_description, 1, 1)
        infos_layout.addWidget(self.chk_inventory, 2, 0)
        infos_layout.addWidget(self.chk_score, 2, 1)
        infos_layout.addWidget(self.chk_won_lost, 3, 0)

        layout.addWidget(infos_group)
        return container

    # ------------------ Agent & Memory Architecture Options ------------------
    def _build_agent_options(self) -> QWidget:
        container = QFrame(self)
        container.setObjectName("ConfigModeCard")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        header = QLabel("MODELO DECISOR & ARQUITECTURA DE MEMORIA", container)
        header.setObjectName("ConfigSectionHeader")

        badge = QLabel("⚡ 2x NVIDIA RTX 4090 (48 GB VRAM)", container)
        badge.setStyleSheet(
            "background-color: rgba(198, 120, 221, 0.15); color: #c678dd; "
            "border: 1px solid #c678dd; border-radius: 4px; padding: 2px 8px; font-size: 10px; font-weight: 700;"
        )

        header_layout.addWidget(header)
        header_layout.addStretch()
        header_layout.addWidget(badge)
        layout.addLayout(header_layout)

        # Cluster Hardware Info Card
        cluster_card = QFrame(container)
        cluster_card.setStyleSheet(
            "background-color: #21252b; border: 1px solid #3e4451; border-radius: 8px; padding: 8px 12px;"
        )
        c_layout = QHBoxLayout(cluster_card)
        c_layout.setContentsMargins(4, 4, 4, 4)

        icon_lbl = QLabel("🖥️", cluster_card)
        icon_lbl.setStyleSheet("font-size: 20px;")

        txt_layout = QVBoxLayout()
        txt_layout.setSpacing(2)
        c_title = QLabel("Cluster Local Activo: 2x NVIDIA GeForce RTX 4090 (Driver 580.173 / CUDA 13.0)", cluster_card)
        c_title.setStyleSheet("color: #98c379; font-size: 11px; font-weight: 700;")
        c_desc = QLabel(
            "Capas y contexto distribuidos en paralelo (GPU 0: 15.5 GB | GPU 1: 15.1 GB) • Ventana de 40K tokens",
            cluster_card,
        )
        c_desc.setStyleSheet("color: #abb2bf; font-size: 10px;")
        txt_layout.addWidget(c_title)
        txt_layout.addWidget(c_desc)

        c_layout.addWidget(icon_lbl)
        c_layout.addLayout(txt_layout, stretch=1)
        layout.addWidget(cluster_card)

        # Selector de agente autónomo activo
        selector_layout = QHBoxLayout()
        selector_lbl = QLabel("Agente Autónomo Activo:", container)
        selector_lbl.setStyleSheet("color: #abb2bf; font-size: 12px; font-weight: 600;")

        self.agent_combo = QComboBox(container)
        self.agent_combo.setObjectName("ConfigComboBox")
        self.agent_combo.setMinimumWidth(320)

        for ag in get_available_agents():
            self.agent_combo.addItem(f"{ag['icon']} {ag['name']}", ag["id"])

        self.agent_combo.currentIndexChanged.connect(self._on_agent_changed)
        selector_layout.addWidget(selector_lbl)
        selector_layout.addWidget(self.agent_combo, stretch=1)
        layout.addLayout(selector_layout)

        # Descripción del agente
        self.agent_desc_lbl = QLabel(container)
        self.agent_desc_lbl.setObjectName("ConfigHintLabel")
        self.agent_desc_lbl.setWordWrap(True)
        self.agent_desc_lbl.setStyleSheet("color: #59e8ff; font-size: 11px; padding: 2px 0;")
        layout.addWidget(self.agent_desc_lbl)

        # Contenedor para controles de Memoria Clásica
        self.history_setting_widget = QWidget(container)
        h_layout = QVBoxLayout(self.history_setting_widget)
        h_layout.setContentsMargins(0, 0, 0, 0)
        self.agent_history_slider, self.agent_history_val_lbl = self._create_slider_control(
            "Ventana de Contexto (Turnos previos):",
            min_val=2,
            max_val=40,
            default_val=self.base_agent_config.classic_history_window,
        )
        h_layout.addLayout(self._wrap_labeled_control(
            "Ventana Deslizante de Memoria Conversacional (LangChain Buffer)",
            self.agent_history_slider,
            self.agent_history_val_lbl,
        ))
        layout.addWidget(self.history_setting_widget)

        # Contenedor para controles de Memoria RAG
        self.rag_setting_widget = QWidget(container)
        r_layout = QVBoxLayout(self.rag_setting_widget)
        r_layout.setContentsMargins(0, 0, 0, 0)
        r_layout.setSpacing(8)

        self.agent_rag_k_slider, self.agent_rag_k_val_lbl = self._create_slider_control(
            "Memorias Relevantes a Recuperar (Top-K):",
            min_val=1,
            max_val=12,
            default_val=self.base_agent_config.rag_top_k,
        )
        r_layout.addLayout(self._wrap_labeled_control(
            "Recuperación Vectorial Semántica de Experiencias (LangChain Top-K)",
            self.agent_rag_k_slider,
            self.agent_rag_k_val_lbl,
        ))

        # Selector de modelo de Embeddings para RAG
        rag_emb_row = QHBoxLayout()
        emb_lbl = QLabel("Modelo de Embeddings (Vectores RAG):", self.rag_setting_widget)
        emb_lbl.setStyleSheet("color: #abb2bf; font-size: 11px; font-weight: 600;")
        self.agent_emb_combo = QComboBox(self.rag_setting_widget)
        self.agent_emb_combo.setObjectName("ConfigComboBox")
        self.agent_emb_combo.addItem("🧠 BGE-M3 (1024 dims - Local 2x RTX 4090)", "bge-m3:latest")
        self.agent_emb_combo.addItem("📝 Nomic Embed Text (274 MB - Local)", "nomic-embed-text:latest")
        self.agent_emb_combo.addItem("⚙️ Fallback Determinístico Local", "local_fallback")
        rag_emb_row.addWidget(emb_lbl)
        rag_emb_row.addWidget(self.agent_emb_combo, stretch=1)
        r_layout.addLayout(rag_emb_row)

        layout.addWidget(self.rag_setting_widget)

        # Contenedor de configuración de hardware central 2x RTX 4090
        self.hw_setting_widget = QGroupBox("Motor Central de Inferencia (2x NVIDIA RTX 4090)", container)
        hw_layout = QVBoxLayout(self.hw_setting_widget)
        hw_layout.setSpacing(10)

        # Fila 1: Selector de Backend / Motor
        backend_row = QHBoxLayout()
        backend_lbl = QLabel("Motor / Backend:", self.hw_setting_widget)
        backend_lbl.setStyleSheet("color: #abb2bf; font-size: 11px; font-weight: 600;")
        backend_lbl.setFixedWidth(135)

        self.backend_combo = QComboBox(self.hw_setting_widget)
        self.backend_combo.setObjectName("ConfigComboBox")
        self.backend_combo.addItem("⚡ Ollama Local (Recomendado 2x RTX 4090 - Puerto 11434)", "ollama")
        self.backend_combo.addItem("🚀 vLLM Servidor Local (Tensor Parallelism tp=2 - Puerto 8000)", "vllm")
        self.backend_combo.addItem("🌐 Endpoint Personalizado / Remoto", "custom")
        self.backend_combo.currentIndexChanged.connect(self._on_backend_changed)

        backend_row.addWidget(backend_lbl)
        backend_row.addWidget(self.backend_combo, stretch=1)
        hw_layout.addLayout(backend_row)

        # Fila 2: Campo de URL personalizada (oculto por defecto)
        self.custom_url_widget = QWidget(self.hw_setting_widget)
        custom_layout = QHBoxLayout(self.custom_url_widget)
        custom_layout.setContentsMargins(0, 0, 0, 0)
        custom_lbl = QLabel("URL Base API:", self.custom_url_widget)
        custom_lbl.setStyleSheet("color: #abb2bf; font-size: 11px;")
        custom_lbl.setFixedWidth(135)
        self.custom_url_edit = QLineEdit(self.base_agent_config.llm_base_url, self.custom_url_widget)
        self.custom_url_edit.setObjectName("ConfigFileLineEdit")
        self.custom_url_edit.setPlaceholderText("http://localhost:11434/v1")
        custom_layout.addWidget(custom_lbl)
        custom_layout.addWidget(self.custom_url_edit, stretch=1)
        self.custom_url_widget.setVisible(False)
        hw_layout.addWidget(self.custom_url_widget)

        # Fila 3: Selector de Modelo Central
        model_row = QHBoxLayout()
        model_lbl = QLabel("Modelo Central LLM:", self.hw_setting_widget)
        model_lbl.setStyleSheet("color: #abb2bf; font-size: 11px; font-weight: 600;")
        model_lbl.setFixedWidth(135)

        self.agent_model_combo = QComboBox(self.hw_setting_widget)
        self.agent_model_combo.setObjectName("ConfigComboBox")
        self.agent_model_combo.setEditable(True)
        self.agent_model_combo.addItem("qwen3:32b", "qwen3:32b")
        self.agent_model_combo.addItem("qwen2.5-coder:32b", "qwen2.5-coder:32b")
        self.agent_model_combo.addItem("qwen2.5:72b", "qwen2.5:72b")
        self.agent_model_combo.addItem("llama3.3:70b", "llama3.3:70b")
        self.agent_model_combo.addItem("gemma4:latest", "gemma4:latest")

        curr_model = self.base_agent_config.llm_model
        idx = self.agent_model_combo.findData(curr_model)
        if idx >= 0:
            self.agent_model_combo.setCurrentIndex(idx)
        else:
            self.agent_model_combo.setEditText(curr_model)

        model_row.addWidget(model_lbl)
        model_row.addWidget(self.agent_model_combo, stretch=1)
        self.agent_model_combo.currentIndexChanged.connect(lambda _: self._update_summary())
        hw_layout.addLayout(model_row)

        # Fila 4: Sliders de Temperatura y Max Tokens
        params_grid = QGridLayout()
        params_grid.setSpacing(10)

        self.agent_temp_slider, self.agent_temp_val_lbl = self._create_slider_control(
            "Temperatura:", min_val=0, max_val=100, default_val=int(self.base_agent_config.temperature * 100)
        )
        self.agent_temp_slider.valueChanged.connect(
            lambda v: self.agent_temp_val_lbl.setText(f"{v / 100.0:.2f}")
        )
        self.agent_temp_val_lbl.setText(f"{self.base_agent_config.temperature:.2f}")

        temp_row = QHBoxLayout()
        temp_lbl = QLabel("Temperatura:", self.hw_setting_widget)
        temp_lbl.setStyleSheet("color: #abb2bf; font-size: 11px;")
        temp_lbl.setFixedWidth(85)
        temp_row.addWidget(temp_lbl)
        temp_row.addWidget(self.agent_temp_slider, stretch=1)
        temp_row.addWidget(self.agent_temp_val_lbl)

        self.agent_tokens_slider, self.agent_tokens_val_lbl = self._create_slider_control(
            "Tokens Máx:", min_val=64, max_val=1024, default_val=self.base_agent_config.max_tokens
        )
        tokens_row = QHBoxLayout()
        tokens_lbl = QLabel("Tokens Máx:", self.hw_setting_widget)
        tokens_lbl.setStyleSheet("color: #abb2bf; font-size: 11px;")
        tokens_lbl.setFixedWidth(85)
        tokens_row.addWidget(tokens_lbl)
        tokens_row.addWidget(self.agent_tokens_slider, stretch=1)
        tokens_row.addWidget(self.agent_tokens_val_lbl)

        params_grid.addLayout(temp_row, 0, 0)
        params_grid.addLayout(tokens_row, 0, 1)
        hw_layout.addLayout(params_grid)

        # Fila 5: Botón de testeo en vivo del LLM y etiqueta de estado
        test_bar = QHBoxLayout()
        self.btn_test_llm = QPushButton("⚡ Probar Conexión con 2x RTX 4090", self.hw_setting_widget)
        self.btn_test_llm.setCursor(Qt.PointingHandCursor)
        self.btn_test_llm.setStyleSheet(
            "QPushButton { background-color: #2c313a; color: #59e8ff; border: 1px solid #61afef; "
            "border-radius: 5px; padding: 5px 12px; font-size: 11px; font-weight: 600; } "
            "QPushButton:hover { background-color: #3b4252; color: #ffffff; border-color: #98c379; } "
            "QPushButton:disabled { background-color: #21252b; color: #5c6370; border-color: #3e4451; }"
        )
        self.btn_test_llm.clicked.connect(self._on_test_llm_clicked)

        self.lbl_llm_status = QLabel("Listo para inferencia", self.hw_setting_widget)
        self.lbl_llm_status.setStyleSheet("color: #98c379; font-size: 11px;")

        test_bar.addWidget(self.btn_test_llm)
        test_bar.addWidget(self.lbl_llm_status, stretch=1)
        hw_layout.addLayout(test_bar)

        layout.addWidget(self.hw_setting_widget)

        # Actualizar visibilidad inicial
        self._on_agent_changed(0)

        return container

    def _on_backend_changed(self, idx: int) -> None:
        backend = self.backend_combo.currentData() or "ollama"
        if hasattr(self, "custom_url_widget"):
            self.custom_url_widget.setVisible(backend == "custom")

    def _on_test_llm_clicked(self) -> None:
        backend = self.backend_combo.currentData() or "ollama"
        if backend == "ollama":
            url = "http://localhost:11434/v1"
        elif backend == "vllm":
            url = "http://localhost:8000/v1"
        else:
            url = self.custom_url_edit.text().strip() or "http://localhost:11434/v1"

        model = self.agent_model_combo.currentText().split()[0].strip()

        self.lbl_llm_status.setStyleSheet("color: #e5c07b; font-size: 11px;")
        self.lbl_llm_status.setText(f"⏳ Consultando {model} en 2x RTX 4090...")
        self.btn_test_llm.setEnabled(False)

        self.llm_test_worker = LLMQuickTestWorker(base_url=url, model=model, parent=self)
        self.llm_test_worker.finished_result.connect(self._on_llm_test_finished)
        self.llm_test_worker.start()

    def _on_llm_test_finished(self, success: bool, message: str, latency: float) -> None:
        self.btn_test_llm.setEnabled(True)
        if success:
            self.lbl_llm_status.setStyleSheet("color: #98c379; font-size: 11px; font-weight: 600;")
            self.lbl_llm_status.setText(f"✅ {message} ({latency:.0f} ms)")
        else:
            self.lbl_llm_status.setStyleSheet("color: #e06c75; font-size: 11px;")
            self.lbl_llm_status.setText(f"❌ {message}")

    def _on_agent_changed(self, idx: int) -> None:
        agent_id = self.agent_combo.currentData() or "random"
        agents = get_available_agents()
        curr = next((a for a in agents if a["id"] == agent_id), None)
        if curr:
            self.agent_desc_lbl.setText(f"{curr['icon']} {curr['description']}")

        is_random = (agent_id == "random")
        is_classic = (agent_id == "classic_memory")
        is_rag = (agent_id == "rag_memory")

        if hasattr(self, "history_setting_widget"):
            self.history_setting_widget.setVisible(is_classic)
        if hasattr(self, "rag_setting_widget"):
            self.rag_setting_widget.setVisible(is_rag)
        if hasattr(self, "hw_setting_widget"):
            self.hw_setting_widget.setVisible(not is_random)

        self._update_summary()

    def _get_selected_agent_config(self) -> tuple[str, dict]:
        agent_type = self.agent_combo.currentData() or "random"
        backend = self.backend_combo.currentData() if hasattr(self, "backend_combo") else "ollama"

        if backend == "ollama":
            llm_url = "http://localhost:11434/v1"
            emb_url = "http://localhost:11434/v1"
        elif backend == "vllm":
            llm_url = "http://localhost:8000/v1"
            emb_url = "http://localhost:8000/v1"
        else:
            llm_url = self.custom_url_edit.text().strip() if hasattr(self, "custom_url_edit") else "http://localhost:11434/v1"
            emb_url = llm_url

        model_name = self.agent_model_combo.currentText().split()[0].strip() if hasattr(self, "agent_model_combo") else "qwen3:32b"
        emb_model = self.agent_emb_combo.currentData() if hasattr(self, "agent_emb_combo") else "bge-m3:latest"
        temp = (self.agent_temp_slider.value() / 100.0) if hasattr(self, "agent_temp_slider") else 0.10
        max_tokens = self.agent_tokens_slider.value() if hasattr(self, "agent_tokens_slider") else 512
        window = self.agent_history_slider.value() if hasattr(self, "agent_history_slider") else 10
        rag_k = self.agent_rag_k_slider.value() if hasattr(self, "agent_rag_k_slider") else 4

        agent_config = {
            "llm_base_url": llm_url or "http://localhost:11434/v1",
            "llm_model": model_name or "qwen3:32b",
            "embedding_base_url": emb_url or "http://localhost:11434/v1",
            "embedding_model": emb_model or "bge-m3:latest",
            "temperature": temp,
            "max_tokens": max_tokens,
            "classic_history_window": window,
            "rag_top_k": rag_k,
            "fallback_if_offline": True,
        }
        return agent_type, agent_config

    def _build_test_options(self) -> QWidget:
        container = QFrame(self)
        container.setObjectName("ConfigTestCard")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        header = QLabel("CONFIGURACIÓN DE TESTEO Y BENCHMARK", container)
        header.setObjectName("ConfigSectionHeader")

        badge = QLabel("MODO EVALUACIÓN", container)
        badge.setObjectName("ConfigTestBadge")
        badge.setStyleSheet(
            "background-color: rgba(97, 175, 239, 0.15); color: #59e8ff; "
            "border: 1px solid #61afef; border-radius: 4px; padding: 2px 8px; font-size: 10px; font-weight: 700;"
        )

        header_layout.addWidget(header)
        header_layout.addStretch()
        header_layout.addWidget(badge)
        layout.addLayout(header_layout)

        # Number of iterations slider
        self.test_iterations_slider, self.test_iterations_val_lbl = self._create_slider_control(
            "Vueltas de Test:", min_val=1, max_val=50, default_val=5
        )
        layout.addLayout(self._wrap_labeled_control("Vueltas / Partidas Autónomas (Episodes)", self.test_iterations_slider, self.test_iterations_val_lbl))

        # Variation mode options
        variation_group = QGroupBox("Variación del Entorno durante el Test")
        var_layout = QHBoxLayout(variation_group)
        var_layout.setSpacing(20)

        self.radio_var_same = QRadioButton("Mismo mundo (1 compilación, múltiples partidas)", variation_group)
        self.radio_var_same.setChecked(True)
        self.radio_var_same.setCursor(Qt.PointingHandCursor)
        self.radio_var_diff = QRadioButton("Mundo nuevo por vuelta (Semillas distintas)", variation_group)
        self.radio_var_diff.setCursor(Qt.PointingHandCursor)

        self.test_var_group = QButtonGroup(self)
        self.test_var_group.addButton(self.radio_var_same, 0)
        self.test_var_group.addButton(self.radio_var_diff, 1)

        var_layout.addWidget(self.radio_var_same)
        var_layout.addWidget(self.radio_var_diff)
        var_layout.addStretch()
        layout.addWidget(variation_group)

        # Execution delay slider (0 ms: instantáneo para benchmark rápido)
        self.test_delay_slider, self.test_delay_val_lbl = self._create_slider_control(
            "Delay por paso (ms):", min_val=0, max_val=200, default_val=0
        )
        layout.addLayout(self._wrap_labeled_control("Velocidad de Simulación (0 ms = Rendimiento Máximo)", self.test_delay_slider, self.test_delay_val_lbl))

        return container

    # ------------------ Action Bar ------------------
    def _build_action_bar(self) -> QWidget:
        action_bar = QWidget(self)
        action_bar.setObjectName("ConfigActionBar")
        layout = QHBoxLayout(action_bar)
        layout.setContentsMargins(25, 14, 25, 14)
        layout.setSpacing(15)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(3)

        self.summary_label = QLabel("Resumen...", action_bar)
        self.summary_label.setObjectName("ConfigSummaryLabel")

        self.status_label = QLabel("Listo para configurar", action_bar)
        self.status_label.setObjectName("ConfigStatusLabel")

        info_layout.addWidget(self.summary_label)
        info_layout.addWidget(self.status_label)

        self.test_button = QPushButton("TESTEAR", action_bar)
        self.test_button.setObjectName("ConfigTestButton")
        self.test_button.setCursor(Qt.PointingHandCursor)
        self.test_button.setMinimumHeight(44)
        self.test_button.setMinimumWidth(150)
        self.test_button.clicked.connect(self._on_test_clicked)

        self.start_button = QPushButton("COMENZAR", action_bar)
        self.start_button.setObjectName("ConfigStartButton")
        self.start_button.setCursor(Qt.PointingHandCursor)
        self.start_button.setMinimumHeight(44)
        self.start_button.setMinimumWidth(160)
        self.start_button.clicked.connect(self._on_start_clicked)

        layout.addLayout(info_layout, stretch=1)
        layout.addWidget(self.test_button)
        layout.addWidget(self.start_button)
        return action_bar

    # ------------------ Helper Builders ------------------
    def _create_slider_control(
        self, label_text: str, min_val: int, max_val: int, default_val: int
    ) -> tuple[QSlider, QLabel]:
        slider = QSlider(Qt.Horizontal)
        slider.setObjectName("ConfigSlider")
        slider.setRange(min_val, max_val)
        slider.setValue(default_val)
        slider.setCursor(Qt.PointingHandCursor)

        val_label = QLabel(str(default_val))
        val_label.setObjectName("ConfigSliderValue")
        val_label.setFixedWidth(30)
        val_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        slider.valueChanged.connect(lambda v: val_label.setText(str(v)))
        return slider, val_label

    def _wrap_labeled_control(self, title: str, control: QWidget, value_widget: QWidget | None = None) -> QVBoxLayout:
        box = QVBoxLayout()
        box.setSpacing(6)

        title_row = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setObjectName("ConfigOptionLabel")
        title_row.addWidget(title_lbl)
        if value_widget:
            title_row.addWidget(value_widget)
        else:
            title_row.addStretch()

        box.addLayout(title_row)
        box.addWidget(control)
        return box

    def _update_summary(self) -> None:
        if not hasattr(self, "summary_label") or self.summary_label is None:
            return
        mode = self.mode_btn_group.checkedId()
        if mode == 0:  # Custom
            rooms = self.rooms_slider.value()
            objects = self.objects_slider.value()
            quest_len = self.quest_len_slider.value()
            theme = self.theme_combo.currentText().split()[0]
            pistas = "Sin pistas (only_last)" if hasattr(self, "chk_only_last") and self.chk_only_last.isChecked() else "Con pistas paso a paso"
            self.summary_label.setText(f"Mundo: {rooms} salas • {objects} objetos • Quest: {quest_len} pasos • Tema: {theme} • {pistas}")
        elif mode == 1:  # File
            path = self.file_path_edit.text()
            name = os.path.basename(path) if path else "Sin archivo"
            self.summary_label.setText(f"Archivo: {name}")
        elif mode == 2:  # Challenge
            ch_name = self.challenge_combo.currentText().split("(")[0].strip()
            lvl = self.difficulty_slider.value()
            pistas = "Sin pistas (only_last)" if hasattr(self, "chk_challenge_only_last") and self.chk_challenge_only_last.isChecked() else "Con pistas paso a paso"
            self.summary_label.setText(f"Desafío: {ch_name} • Nivel: {lvl} • {pistas}")

        if hasattr(self, "agent_combo") and self.agent_combo.currentText():
            agent_txt = self.agent_combo.currentText()
            agent_id = self.agent_combo.currentData() or "random"
            if agent_id != "random" and hasattr(self, "agent_model_combo"):
                model_txt = self.agent_model_combo.currentText().split()[0]
                self.summary_label.setText(self.summary_label.text() + f" | {agent_txt} ({model_txt} @ 2x 4090)")
            else:
                self.summary_label.setText(self.summary_label.text() + f" | {agent_txt}")

    def _validate_config_preflight(self, mode_id: int) -> tuple[bool, str]:
        """Comprueba que la configuración sea básica y viable para evitar errores inmediatos."""
        if mode_id == 0:  # Custom
            rooms = self.rooms_slider.value()
            quest_len = self.quest_len_slider.value()
            quest_breadth = self.quest_breadth_slider.value()

            if quest_len <= 2 and quest_breadth > 1:
                return False, "Inviable: No se pueden generar subquests ramificadas con una longitud menor a 3 pasos."
            if rooms == 1 and self.parallel_spin.value() > 2:
                return False, "Inviable: Un mundo de 1 sala no admite más de 2 misiones paralelas independientes."
        elif mode_id == 1:  # File
            path = self.file_path_edit.text().strip()
            if not path or not os.path.exists(path):
                return False, "Por favor selecciona un archivo de juego (.z8) válido que exista."
        elif mode_id == 2:  # Challenge
            level = self.difficulty_slider.value()
            if level < 1 or level > 30:
                return False, "El nivel del desafío debe estar entre 1 y 30."
        return True, ""

    # ------------------ Game Launch Logic ------------------
    def _on_start_clicked(self) -> None:
        mode_id = self.mode_btn_group.checkedId()
        is_valid, err_msg = self._validate_config_preflight(mode_id)
        if not is_valid:
            self.status_label.setStyleSheet("color: #e06c75; font-size: 11px;")
            self.status_label.setText(f"⚠️ {err_msg}")
            return

        max_steps = self.max_steps_slider.value()

        request_infos = EnvInfos(
            admissible_commands=True,
            location=True,
            facts=True,
            description=self.chk_description.isChecked(),
            inventory=self.chk_inventory.isChecked(),
            score=self.chk_score.isChecked(),
            won=self.chk_won_lost.isChecked(),
            lost=self.chk_won_lost.isChecked(),
        )

        config: dict = {}
        mode_str = "custom"

        if mode_id == 0:
            mode_str = "custom"
            seed_val = None if self.chk_random_seed.isChecked() else self.seed_spin.value()
            config = {
                "nb_rooms": self.rooms_slider.value(),
                "nb_objects": self.objects_slider.value(),
                "quest_length": self.quest_len_slider.value(),
                "quest_breadth": self.quest_breadth_slider.value(),
                "nb_parallel_quests": self.parallel_spin.value(),
                "subquests": self.chk_subquests.isChecked(),
                "independent_chains": self.chk_independent.isChecked(),
                "theme": self.theme_combo.currentData(),
                "include_adj": self.chk_include_adj.isChecked(),
                "blend_descriptions": self.chk_blend_desc.isChecked(),
                "blend_instructions": self.chk_blend_inst.isChecked(),
                "only_last_action": self.chk_only_last.isChecked(),
                "ambiguous_instructions": False,
                "entity_numbering": self.chk_numbering.isChecked(),
                "seed": seed_val,
            }
            self.status_label.setStyleSheet("color: #59e8ff; font-size: 11px;")
            self.status_label.setText("Generando y compilando mundo TextWorld...")
        elif mode_id == 1:
            mode_str = "file"
            file_path = self.file_path_edit.text().strip()
            config = {"file_path": file_path}
            self.status_label.setStyleSheet("color: #59e8ff; font-size: 11px;")
            self.status_label.setText("Cargando archivo de juego...")
        elif mode_id == 2:
            mode_str = "challenge"
            seed_val = None if self.chk_challenge_random_seed.isChecked() else self.challenge_seed_spin.value()
            config = {
                "challenge_type": self.challenge_combo.currentData(),
                "level": int(self.difficulty_slider.value()),
                "seed": seed_val,
                "only_last_action": self.chk_challenge_only_last.isChecked(),
            }
            self.status_label.setStyleSheet("color: #59e8ff; font-size: 11px;")
            self.status_label.setText("Generando desafío TextWorld...")

        self.start_button.setEnabled(False)
        self.test_button.setEnabled(False)
        self.start_button.setCursor(Qt.ForbiddenCursor)
        self.test_button.setCursor(Qt.ForbiddenCursor)

        # Background generation worker
        self.worker = GameGeneratorWorker(
            mode=mode_str,
            config=config,
            max_steps=max_steps,
            request_infos=request_infos,
            parent=self,
        )
        self.worker.finished_success.connect(self._on_worker_success)
        self.worker.finished_error.connect(self._on_worker_error)
        self.worker.start()

    def _on_test_clicked(self) -> None:
        mode_id = self.mode_btn_group.checkedId()
        is_valid, err_msg = self._validate_config_preflight(mode_id)
        if not is_valid:
            self.status_label.setStyleSheet("color: #e06c75; font-size: 11px;")
            self.status_label.setText(f"⚠️ {err_msg}")
            return

        max_steps = self.max_steps_slider.value()

        request_infos = EnvInfos(
            admissible_commands=True,
            location=True,
            facts=True,
            description=self.chk_description.isChecked(),
            inventory=self.chk_inventory.isChecked(),
            score=self.chk_score.isChecked(),
            won=self.chk_won_lost.isChecked(),
            lost=self.chk_won_lost.isChecked(),
        )

        config: dict = {}
        mode_str = "custom"

        if mode_id == 0:
            mode_str = "custom"
            seed_val = None if self.chk_random_seed.isChecked() else self.seed_spin.value()
            config = {
                "nb_rooms": self.rooms_slider.value(),
                "nb_objects": self.objects_slider.value(),
                "quest_length": self.quest_len_slider.value(),
                "quest_breadth": self.quest_breadth_slider.value(),
                "nb_parallel_quests": self.parallel_spin.value(),
                "subquests": self.chk_subquests.isChecked(),
                "independent_chains": self.chk_independent.isChecked(),
                "theme": self.theme_combo.currentData(),
                "include_adj": self.chk_include_adj.isChecked(),
                "blend_descriptions": self.chk_blend_desc.isChecked(),
                "blend_instructions": self.chk_blend_inst.isChecked(),
                "only_last_action": self.chk_only_last.isChecked(),
                "ambiguous_instructions": False,
                "entity_numbering": self.chk_numbering.isChecked(),
                "seed": seed_val,
            }
        elif mode_id == 1:
            mode_str = "file"
            file_path = self.file_path_edit.text().strip()
            config = {"file_path": file_path}
        elif mode_id == 2:
            mode_str = "challenge"
            seed_val = None if self.chk_challenge_random_seed.isChecked() else self.challenge_seed_spin.value()
            config = {
                "challenge_type": self.challenge_combo.currentData(),
                "level": int(self.difficulty_slider.value()),
                "seed": seed_val,
                "only_last_action": self.chk_challenge_only_last.isChecked(),
            }

        test_config = {
            "num_iterations": self.test_iterations_slider.value(),
            "variation_mode": "same_world" if (self.radio_var_same.isChecked() or mode_id == 1) else "distinct_seeds",
            "step_delay_ms": self.test_delay_slider.value(),
        }

        agent_type, agent_config = self._get_selected_agent_config()
        test_config["agent_type"] = agent_type
        test_config["agent_config"] = agent_config

        if self.on_start_test:
            self.on_start_test(mode_str, config, test_config, max_steps, request_infos, agent_type, agent_config)

    def _on_worker_success(self, game_path: str, max_steps: int, request_infos: EnvInfos) -> None:
        self.status_label.setStyleSheet("color: #59ff93; font-size: 11px;")
        self.status_label.setText("¡Mundo generado con éxito! Iniciando...")
        self.start_button.setEnabled(True)
        self.test_button.setEnabled(True)
        self.start_button.setCursor(Qt.PointingHandCursor)
        self.test_button.setCursor(Qt.PointingHandCursor)
        if self.on_start_game:
            agent_type, agent_config = self._get_selected_agent_config()
            self.on_start_game(game_path, max_steps, request_infos, agent_type, agent_config)

    def _on_worker_error(self, error_message: str) -> None:
        self.status_label.setStyleSheet("color: #e06c75; font-size: 11px;")
        self.status_label.setText(f"Error al generar: {error_message}")
        self.start_button.setEnabled(True)
        self.test_button.setEnabled(True)
        self.start_button.setCursor(Qt.PointingHandCursor)
        self.test_button.setCursor(Qt.PointingHandCursor)
