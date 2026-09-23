from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from controllers.test_controller import list_saved_test_sessions


class MenuOptionCard(QFrame):
    """Tarjeta interactiva para el menú principal con estética profesional."""

    def __init__(
        self,
        badge_text: str,
        badge_color: str,
        title: str,
        description: str,
        button_text: str,
        on_click: Callable[[], None] | None = None,
        is_disabled: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("MainMenuCardDisabled" if is_disabled else "MainMenuCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)

        # Header con Badge
        top_row = QHBoxLayout()
        badge = QLabel(badge_text, self)
        badge.setStyleSheet(
            f"background-color: {badge_color}22; color: {badge_color}; "
            f"border: 1px solid {badge_color}; border-radius: 4px; padding: 3px 9px; "
            "font-size: 10px; font-weight: 800; letter-spacing: 1px;"
        )
        top_row.addWidget(badge)
        top_row.addStretch()

        if is_disabled:
            lock_label = QLabel("🔒 BLOQUEADO", self)
            lock_label.setStyleSheet("color: #e5c07b; font-size: 10px; font-weight: 800;")
            top_row.addWidget(lock_label)

        layout.addLayout(top_row)

        # Título
        title_label = QLabel(title, self)
        title_label.setObjectName("MainMenuCardTitle")
        layout.addWidget(title_label)

        # Descripción
        desc_label = QLabel(description, self)
        desc_label.setObjectName("MainMenuCardDesc")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        layout.addStretch()

        # Botón de Acción
        btn = QPushButton(button_text, self)
        if is_disabled:
            btn.setObjectName("MainMenuButtonDisabled")
            btn.setEnabled(False)
            btn.setCursor(Qt.ForbiddenCursor)
        else:
            btn.setObjectName("MainMenuButtonActive")
            btn.setCursor(Qt.PointingHandCursor)
            if on_click:
                btn.clicked.connect(on_click)

        btn.setMinimumHeight(44)
        layout.addWidget(btn)


class MainMenuPanel(QWidget):
    """Pantalla inicial / Menú Principal de la aplicación."""

    open_config_requested = Signal()
    open_results_requested = Signal()

    def __init__(
        self,
        on_open_config: Callable[[], None] | None = None,
        on_open_results: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("MainMenuContainer")

        if on_open_config:
            self.open_config_requested.connect(on_open_config)
        if on_open_results:
            self.open_results_requested.connect(on_open_results)

        self._build_ui()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Cabecera Hero
        root_layout.addWidget(self._build_hero_header())

        # 2. Contenedor de Opciones (Centrado y con scroll)
        scroll = QScrollArea(self)
        scroll.setObjectName("ConfigScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget(scroll)
        content.setObjectName("MainMenuContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(40, 30, 40, 30)
        content_layout.setSpacing(25)
        content_layout.setAlignment(Qt.AlignCenter)

        # Tarjetas de opciones principales (Grid horizontal de 3 opciones)
        cards_row = QHBoxLayout()
        cards_row.setSpacing(24)

        # Opción 1: Configurar
        card_config = MenuOptionCard(
            badge_text="MUNDO & PARTIDA",
            badge_color="#61afef",
            title="Configurar Entorno",
            description=(
                "Genera mundos procedurales personalizados (habitaciones, objetos, misiones), "
                "carga archivos de juego precompilados (.z8) o desafíos TextWorld, y lanza partidas "
                "interactivas o benchmarks de testeo autónomo."
            ),
            button_text="IR A CONFIGURACIÓN ➔",
            on_click=self.open_config_requested.emit,
        )
        card_config.setMinimumWidth(320)
        card_config.setMaximumWidth(420)
        card_config.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        # Opción 2: Revisar Tests
        card_results = MenuOptionCard(
            badge_text="BENCHMARK & HISTORIAL",
            badge_color="#98c379",
            title="Revisar Test Específico",
            description=(
                "Consulta directamente el historial de sesiones de testeo y diagnósticos guardados. "
                "Analiza métricas de eficacia (% victorias), eficiencia en pasos y visualiza la "
                "representación espacial de cada partida sin iniciar una nueva simulación."
            ),
            button_text="VER HISTORIAL DE TESTS ➔",
            on_click=self.open_results_requested.emit,
        )
        card_results.setMinimumWidth(320)
        card_results.setMaximumWidth(420)
        card_results.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        # Opción 3: Configurar Agente (Deshabilitado)
        card_agent = MenuOptionCard(
            badge_text="INTELIGENCIA & MODELOS",
            badge_color="#c678dd",
            title="Configuración del Agente",
            description=(
                "Personaliza la arquitectura del agente decisor: conexión a modelos de lenguaje (LLMs), "
                "definición de prompts del sistema, estrategias de exploración espacial y parámetros "
                "de inferencia (temperatura, tokens)."
            ),
            button_text="PRÓXIMAMENTE (EN DESARROLLO)",
            is_disabled=True,
        )
        card_agent.setMinimumWidth(320)
        card_agent.setMaximumWidth(420)
        card_agent.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        cards_row.addWidget(card_config)
        cards_row.addWidget(card_results)
        cards_row.addWidget(card_agent)

        content_layout.addLayout(cards_row)

        scroll.setWidget(content)
        root_layout.addWidget(scroll, stretch=1)

        # 3. Footer / Barra inferior de estado
        root_layout.addWidget(self._build_footer())

    def _build_hero_header(self) -> QWidget:
        header = QWidget(self)
        header.setObjectName("MainMenuHero")
        layout = QVBoxLayout(header)
        layout.setContentsMargins(40, 32, 40, 26)
        layout.setSpacing(8)

        tag = QLabel("TEXTWORLD AI AGENT PLATFORM", header)
        tag.setObjectName("ConfigHeaderTag")

        title = QLabel("Menú Principal de Simulación", header)
        title.setObjectName("MainMenuHeroTitle")

        subtitle = QLabel(
            "Selecciona una opción para comenzar: configura un nuevo mundo o prueba, "
            "inspecciona resultados de evaluaciones anteriores o ajusta parámetros.",
            header,
        )
        subtitle.setObjectName("MainMenuHeroSubtitle")

        layout.addWidget(tag)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        return header

    def _build_footer(self) -> QWidget:
        footer = QWidget(self)
        footer.setObjectName("MainMenuFooter")
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(40, 16, 40, 16)

        sessions_count = len(list_saved_test_sessions())
        self.sessions_label = QLabel(
            f"📁 {sessions_count} sesiones de test guardadas en el sistema • Motor TextWorld: Activo",
            footer,
        )
        self.sessions_label.setStyleSheet("color: #abb2bf; font-size: 11px;")

        hint_label = QLabel("💡 Puedes regresar a este menú en cualquier momento desde cualquier panel", footer)
        hint_label.setStyleSheet("color: #5c6370; font-size: 11px; font-style: italic;")

        layout.addWidget(self.sessions_label)
        layout.addStretch()
        layout.addWidget(hint_label)
        return footer

    def refresh_sessions_count(self) -> None:
        """Actualiza el contador de sesiones guardadas en la barra inferior."""
        count = len(list_saved_test_sessions())
        self.sessions_label.setText(
            f"📁 {count} sesiones de test guardadas en el sistema • Motor TextWorld: Activo"
        )
