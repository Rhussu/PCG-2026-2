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
    """Tarjeta interactiva para el menú principal con estética moderna y minimalista."""

    def __init__(
        self,
        badge_text: str,
        badge_color: str,
        title: str,
        description: str,
        button_text: str,
        button_object_name: str = "MainMenuButtonActive",
        on_click: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("MainMenuCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(14)

        # Header con Badge Temático
        top_row = QHBoxLayout()
        badge = QLabel(badge_text, self)
        badge.setStyleSheet(
            f"background-color: {badge_color}1a; color: {badge_color}; "
            f"border: 1px solid {badge_color}88; border-radius: 6px; padding: 4px 10px; "
            "font-size: 11px; font-weight: 800; letter-spacing: 0.8px;"
        )
        top_row.addWidget(badge)
        top_row.addStretch()
        layout.addLayout(top_row)

        # Título de la tarjeta
        title_label = QLabel(title, self)
        title_label.setObjectName("MainMenuCardTitle")
        layout.addWidget(title_label)

        # Descripción
        desc_label = QLabel(description, self)
        desc_label.setObjectName("MainMenuCardDesc")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        layout.addStretch()

        # Botón de Acción Call-To-Action
        btn = QPushButton(button_text, self)
        btn.setObjectName(button_object_name)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setMinimumHeight(46)
        if on_click:
            btn.clicked.connect(on_click)

        layout.addWidget(btn)


class MainMenuPanel(QWidget):
    """Pantalla inicial / Menú Principal de la aplicación con diseño dual centrado y minimalista."""

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

        # 2. Contenedor de Opciones (Centrado y con scroll suave)
        scroll = QScrollArea(self)
        scroll.setObjectName("ConfigScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget(scroll)
        content.setObjectName("MainMenuContent")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(40, 40, 40, 40)
        content_layout.setSpacing(25)
        content_layout.setAlignment(Qt.AlignCenter)

        # Fila de tarjetas: 2 opciones simétricas
        cards_row = QHBoxLayout()
        cards_row.setSpacing(32)
        cards_row.setAlignment(Qt.AlignCenter)

        # Opción 1: Configurar Simulación & Entorno
        card_config = MenuOptionCard(
            badge_text="🎮 MUNDO & SIMULACIÓN",
            badge_color="#61afef",
            title="Configurar Simulación",
            description=(
                "Genera mundos procedurales, carga mapas precompilados (.z8) o desafíos TextWorld. "
                "Selecciona el modelo decisor (Historial Clásico, RAG o Baseline) y lanza partidas "
                "interactivas paso a paso o suites de evaluación continua."
            ),
            button_text="CONFIGURAR PARTIDA ➔",
            button_object_name="MainMenuButtonActive",
            on_click=self.open_config_requested.emit,
        )
        card_config.setMinimumWidth(380)
        card_config.setMaximumWidth(460)
        card_config.setMinimumHeight(320)
        card_config.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        # Opción 2: Revisar Resultados & Diagnóstico
        card_results = MenuOptionCard(
            badge_text="📊 BENCHMARK & RESULTADOS",
            badge_color="#98c379",
            title="Historial & Diagnóstico",
            description=(
                "Consulta y audita el rendimiento histórico de las sesiones guardadas. "
                "Analiza tasas de victoria, eficiencia en pasos, consumo de tokens en 2x 4090, "
                "latencias por decisión y visualiza la evolución del mapa explorado."
            ),
            button_text="EXPLORAR RESULTADOS ➔",
            button_object_name="MainMenuButtonResults",
            on_click=self.open_results_requested.emit,
        )
        card_results.setMinimumWidth(380)
        card_results.setMaximumWidth(460)
        card_results.setMinimumHeight(320)
        card_results.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        cards_row.addWidget(card_config)
        cards_row.addWidget(card_results)

        content_layout.addLayout(cards_row)

        scroll.setWidget(content)
        root_layout.addWidget(scroll, stretch=1)

        # 3. Footer / Barra inferior de estado
        root_layout.addWidget(self._build_footer())

    def _build_hero_header(self) -> QWidget:
        header = QWidget(self)
        header.setObjectName("MainMenuHero")
        layout = QVBoxLayout(header)
        layout.setContentsMargins(40, 36, 40, 26)
        layout.setSpacing(8)

        tag = QLabel("TEXTWORLD AI BENCHMARK PLATFORM", header)
        tag.setObjectName("ConfigHeaderTag")

        title = QLabel("Menú Principal de Simulación", header)
        title.setObjectName("MainMenuHeroTitle")

        subtitle = QLabel(
            "Plataforma de evaluación espacio-temporal para agentes autónomos con memoria. "
            "Selecciona una modalidad para comenzar:",
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

        hint_label = QLabel("💡 Puedes regresar a este menú en cualquier momento desde cualquier pantalla", footer)
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
