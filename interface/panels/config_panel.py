from __future__ import annotations

import os
import random
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
                opts.grammar.ambiguous_instructions = self.config.get("ambiguous_instructions", False)
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
                if self.config.get("seed") is not None:
                    opts.seeds = int(self.config["seed"])

                settings = {}
                if ch_type == "tw-treasure_hunter":
                    settings["level"] = str(self.config.get("level", 1))
                elif ch_type == "tw-coin_collector":
                    settings["level"] = str(self.config.get("level", 1))

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


class ConfigPanel(QWidget):
    def __init__(
        self,
        on_start_game: Callable[[str, int, EnvInfos], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.on_start_game = on_start_game
        self.setObjectName("RightPanel")
        self.worker: GameGeneratorWorker | None = None

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
        self.radio_file = QRadioButton("Cargar Juego (.z8)", container)
        self.radio_challenge = QRadioButton("Desafíos TextWorld", container)

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
        self.quest_len_slider.valueChanged.connect(self._update_summary)
        quest_layout.addLayout(self._wrap_labeled_control("Longitud de Misión", self.quest_len_slider, self.quest_len_val_lbl))

        # Quest breadth
        self.quest_breadth_slider, self.quest_breadth_val_lbl = self._create_slider_control(
            "Amplitud de Subquests (Breadth):", min_val=1, max_val=5, default_val=1
        )
        self.quest_breadth_slider.valueChanged.connect(self._update_summary)
        quest_layout.addLayout(self._wrap_labeled_control("Amplitud (Sub-misiones paralelas)", self.quest_breadth_slider, self.quest_breadth_val_lbl))

        # Parallel quests spinbox
        parallel_row = QHBoxLayout()
        parallel_lbl = QLabel("Misiones Paralelas Independientes:")
        parallel_lbl.setObjectName("ConfigOptionLabel")
        self.parallel_spin = QSpinBox()
        self.parallel_spin.setRange(1, 4)
        self.parallel_spin.setValue(1)
        self.parallel_spin.valueChanged.connect(self._update_summary)
        parallel_row.addWidget(parallel_lbl)
        parallel_row.addWidget(self.parallel_spin)
        parallel_row.addStretch()
        quest_layout.addLayout(parallel_row)

        # Advanced quest toggles
        adv_group = QGroupBox("Opciones Avanzadas de Chaining")
        adv_layout = QVBoxLayout(adv_group)
        self.chk_subquests = QCheckBox("Permitir submisiones incompletas (subquests abiertas)")
        self.chk_independent = QCheckBox("Permitir cadenas de quests totalmente independientes")
        adv_layout.addWidget(self.chk_subquests)
        adv_layout.addWidget(self.chk_independent)
        quest_layout.addWidget(adv_group)
        quest_layout.addStretch()

        tab_widget.addTab(tab_quest, "🎯 Misión")

        # Tab 3: Lenguaje y Gramática
        tab_grammar = QWidget()
        grammar_layout = QVBoxLayout(tab_grammar)
        grammar_layout.setContentsMargins(16, 16, 16, 16)
        grammar_layout.setSpacing(12)

        self.chk_include_adj = QCheckBox("Incluir adjetivos en nombres de entidades (ej. red apple)")
        self.chk_include_adj.setChecked(True)
        self.chk_blend_desc = QCheckBox("Fusionar descripciones entre oraciones consecutivas")
        self.chk_blend_desc.setChecked(True)
        self.chk_blend_inst = QCheckBox("Fusionar instrucciones consecutivas en una sola frase")
        self.chk_only_last = QCheckBox("Objetivo describe sólo la última acción de la misión")
        self.chk_ambiguous = QCheckBox("Instrucciones ambiguas usando tipos de objetos (ej. container)")
        self.chk_numbering = QCheckBox("Numerar entidades duplicadas (ej. 'key 1', 'key 2')")
        self.chk_numbering.setChecked(True)

        grammar_layout.addWidget(self.chk_include_adj)
        grammar_layout.addWidget(self.chk_blend_desc)
        grammar_layout.addWidget(self.chk_blend_inst)
        grammar_layout.addWidget(self.chk_only_last)
        grammar_layout.addWidget(self.chk_ambiguous)
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
        self.chk_random_seed.toggled.connect(self._on_random_seed_toggled)

        seed_input_row = QHBoxLayout()
        seed_lbl = QLabel("Semilla Fija (Reproducible):")
        seed_lbl.setObjectName("ConfigOptionLabel")
        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(0, 999999)
        self.seed_spin.setValue(42)
        self.seed_spin.setEnabled(False)

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

    def _on_random_seed_toggled(self, checked: bool) -> None:
        self.seed_spin.setEnabled(not checked)

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

        browse_btn = QPushButton("Examinar...")
        browse_btn.setObjectName("ConfigBrowseButton")
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

    def _on_predefined_file_selected(self, index: int) -> None:
        path = self.file_combo.itemData(index)
        if path:
            self.file_path_edit.setText(path)
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
        self.challenge_combo.currentIndexChanged.connect(self._update_summary)

        challenge_row.addWidget(challenge_lbl)
        challenge_row.addWidget(self.challenge_combo, stretch=1)
        layout.addLayout(challenge_row)

        self.difficulty_slider, self.difficulty_val_lbl = self._create_slider_control(
            "Nivel de Dificultad (Level):", min_val=1, max_val=30, default_val=1
        )
        layout.addLayout(self._wrap_labeled_control("Dificultad (1-30)", self.difficulty_slider, self.difficulty_val_lbl))

        hint = QLabel("Los desafíos TextWorld generan problemas estandarizados con misiones graduadas en complejidad.")
        hint.setObjectName("ConfigHintLabel")
        layout.addWidget(hint)
        layout.addStretch()

        return widget

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

        self.chk_location = QCheckBox("Localización (location)")
        self.chk_location.setChecked(True)
        self.chk_location.setEnabled(False)  # Requerido por el mapa

        self.chk_facts = QCheckBox("Hechos del Mundo (facts)")
        self.chk_facts.setChecked(True)
        self.chk_facts.setEnabled(False)     # Requerido por el mapa

        self.chk_commands = QCheckBox("Comandos Admisibles (admissible_commands)")
        self.chk_commands.setChecked(True)
        self.chk_commands.setEnabled(False)  # Requerido por el agente

        self.chk_description = QCheckBox("Descripción de sala (description)")
        self.chk_description.setChecked(True)

        self.chk_inventory = QCheckBox("Inventario (inventory)")
        self.chk_inventory.setChecked(True)

        self.chk_score = QCheckBox("Puntuación (score)")
        self.chk_score.setChecked(True)

        self.chk_won_lost = QCheckBox("Victoria / Derrota (won / lost)")
        self.chk_won_lost.setChecked(True)

        infos_layout.addWidget(self.chk_location, 0, 0)
        infos_layout.addWidget(self.chk_facts, 0, 1)
        infos_layout.addWidget(self.chk_commands, 1, 0)
        infos_layout.addWidget(self.chk_description, 1, 1)
        infos_layout.addWidget(self.chk_inventory, 2, 0)
        infos_layout.addWidget(self.chk_score, 2, 1)
        infos_layout.addWidget(self.chk_won_lost, 3, 0)

        layout.addWidget(infos_group)
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

        self.start_button = QPushButton("COMENZAR", action_bar)
        self.start_button.setObjectName("ConfigStartButton")
        self.start_button.setCursor(Qt.PointingHandCursor)
        self.start_button.setMinimumHeight(44)
        self.start_button.setMinimumWidth(160)
        self.start_button.clicked.connect(self._on_start_clicked)

        layout.addLayout(info_layout, stretch=1)
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
        mode = self.mode_btn_group.checkedId()
        if mode == 0:  # Custom
            rooms = self.rooms_slider.value()
            objects = self.objects_slider.value()
            quest_len = self.quest_len_slider.value()
            theme = self.theme_combo.currentText().split()[0]
            self.summary_label.setText(f"Mundo: {rooms} salas • {objects} objetos • Quest: {quest_len} pasos • Tema: {theme}")
        elif mode == 1:  # File
            path = self.file_path_edit.text()
            name = os.path.basename(path) if path else "Sin archivo"
            self.summary_label.setText(f"Archivo: {name}")
        elif mode == 2:  # Challenge
            ch_name = self.challenge_combo.currentText().split("(")[0].strip()
            lvl = self.difficulty_slider.value()
            self.summary_label.setText(f"Desafío: {ch_name} • Nivel: {lvl}")

    # ------------------ Game Launch Logic ------------------
    def _on_start_clicked(self) -> None:
        mode_id = self.mode_btn_group.checkedId()
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
                "ambiguous_instructions": self.chk_ambiguous.isChecked(),
                "entity_numbering": self.chk_numbering.isChecked(),
                "seed": seed_val,
            }
            self.status_label.setText("Generando y compilando mundo TextWorld...")
        elif mode_id == 1:
            mode_str = "file"
            file_path = self.file_path_edit.text().strip()
            if not file_path:
                self.status_label.setText("Error: Selecciona un archivo válido")
                return
            config = {"file_path": file_path}
            self.status_label.setText("Cargando archivo de juego...")
        elif mode_id == 2:
            mode_str = "challenge"
            seed_val = None if self.chk_random_seed.isChecked() else self.seed_spin.value()
            config = {
                "challenge_type": self.challenge_combo.currentData(),
                "level": self.difficulty_slider.value(),
                "seed": seed_val,
            }
            self.status_label.setText("Generando desafío TextWorld...")

        self.start_button.setEnabled(False)

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

    def _on_worker_success(self, game_path: str, max_steps: int, request_infos: EnvInfos) -> None:
        self.status_label.setText("¡Mundo generado con éxito! Iniciando...")
        self.start_button.setEnabled(True)
        if self.on_start_game:
            self.on_start_game(game_path, max_steps, request_infos)

    def _on_worker_error(self, error_message: str) -> None:
        self.status_label.setText(f"Error al generar: {error_message}")
        self.start_button.setEnabled(True)
