from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from controllers.chat_controller import ChatController


# ==============================================================================
# 1. MODAL DE INSPECCIÓN COMPLETA DE REPRESENTACIÓN / ARCHIVO
# ==============================================================================
class RepresentationViewerDialog(QDialog):
    """Diálogo modal moderno y oscuro para visualizar en su totalidad
    el archivo de historial conversacional o el almacén vectorial RAG.
    """

    def __init__(
        self,
        title: str,
        filename: str,
        content_text: str,
        subtitle: str = "",
        details_data: dict[str, Any] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Inspección de Memoria — {filename}")
        self.resize(820, 620)
        self.setMinimumSize(600, 450)
        self.setObjectName("RepresentationViewerModal")

        self.filename = filename
        self.content_text = content_text
        self.details_data = details_data or {}

        # Layout principal
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 18, 20, 18)
        root_layout.setSpacing(14)

        # 1. Cabecera con icono, título y metadata
        header_widget = QWidget(self)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        icon_label = QLabel("📄" if "txt" in filename or "md" in filename else "🗄️", header_widget)
        icon_label.setStyleSheet("font-size: 28px;")
        header_layout.addWidget(icon_label)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        lbl_filename = QLabel(filename, header_widget)
        lbl_filename.setStyleSheet("font-size: 15px; font-weight: 700; color: #ffffff;")
        lbl_sub = QLabel(subtitle or title, header_widget)
        lbl_sub.setStyleSheet("font-size: 11px; color: #61afef; font-weight: 600;")
        title_layout.addWidget(lbl_filename)
        title_layout.addWidget(lbl_sub)
        header_layout.addLayout(title_layout, stretch=1)

        # Botones de acción en la cabecera
        self.btn_copy = QPushButton("📋 Copiar Contenido", header_widget)
        self.btn_copy.setObjectName("RepresentationModalBtn")
        self.btn_copy.setCursor(Qt.PointingHandCursor)
        self.btn_copy.clicked.connect(self._copy_to_clipboard)

        self.btn_save = QPushButton("💾 Guardar...", header_widget)
        self.btn_save.setObjectName("RepresentationModalBtn")
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.clicked.connect(self._save_to_disk)

        self.btn_close = QPushButton("✕", header_widget)
        self.btn_close.setObjectName("RepresentationModalCloseBtn")
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setFixedSize(28, 28)
        self.btn_close.clicked.connect(self.accept)

        header_layout.addWidget(self.btn_copy)
        header_layout.addWidget(self.btn_save)
        header_layout.addWidget(self.btn_close)
        root_layout.addWidget(header_widget)

        # Barra separadora
        divider = QFrame(self)
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFrameShadow(QFrame.Shadow.Plain)
        divider.setStyleSheet("background-color: #3e4451; max-height: 1px;")
        root_layout.addWidget(divider)

        # 2. Visor de contenido
        if self.details_data and "memories" in self.details_data:
            # Modo pestañas para RAG: Volcado de texto plano + Explorador de chunks
            tabs = QTabWidget(self)
            tabs.setObjectName("RepresentationTabs")

            # Tab 1: Volcado de Texto
            txt_edit = self._create_text_editor(self.content_text)
            tabs.addTab(txt_edit, "📄 Volcado Completo")

            # Tab 2: Explorador de fragmentos
            chunks_widget = self._create_chunks_explorer(self.details_data)
            tabs.addTab(chunks_widget, "🔍 Fragmentos y Embeddings")

            root_layout.addWidget(tabs, stretch=1)
        else:
            # Modo directo: Visor de texto plano
            txt_edit = self._create_text_editor(self.content_text)
            root_layout.addWidget(txt_edit, stretch=1)

        # 3. Pie con estadísticas
        footer_label = QLabel(self._build_footer_stats(), self)
        footer_label.setStyleSheet("color: #7f848e; font-size: 11px;")
        root_layout.addWidget(footer_label)

    def _create_text_editor(self, text: str) -> QPlainTextEdit:
        editor = QPlainTextEdit(self)
        editor.setReadOnly(True)
        editor.setPlainText(text)
        editor.setStyleSheet(
            """
            QPlainTextEdit {
                background-color: #1e2227;
                color: #abb2bf;
                border: 1px solid #3e4451;
                border-radius: 8px;
                padding: 12px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                line-height: 1.4;
            }
            """
        )
        return editor

    def _create_chunks_explorer(self, data: dict[str, Any]) -> QWidget:
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(8)

        scroll = QScrollArea(container)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background-color: transparent;")

        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(6)

        memories = data.get("memories", [])
        if not memories:
            empty_lbl = QLabel("(No hay fragmentos indexados en este almacén)", inner)
            empty_lbl.setStyleSheet("color: #7f848e; font-style: italic; padding: 10px;")
            inner_layout.addWidget(empty_lbl)
        else:
            for idx, mem in enumerate(memories):
                card = QFrame(inner)
                card.setStyleSheet(
                    """
                    QFrame {
                        background-color: #21252b;
                        border: 1px solid #3e4451;
                        border-radius: 6px;
                        padding: 8px;
                    }
                    """
                )
                c_layout = QVBoxLayout(card)
                c_layout.setContentsMargins(8, 8, 8, 8)
                c_layout.setSpacing(4)

                top_row = QHBoxLayout()
                cat = mem.get("category", "info").upper()
                step = mem.get("step", 0)
                is_ret = mem.get("is_retrieved", False)
                score = mem.get("retrieval_score")

                cat_color = "#61afef" if "OBS" in cat else "#c678dd"
                lbl_tag = QLabel(f"[{cat}]", card)
                lbl_tag.setStyleSheet(f"color: {cat_color}; font-weight: 700; font-size: 10px;")
                top_row.addWidget(lbl_tag)

                lbl_step = QLabel(f"Turno/Paso {step}", card)
                lbl_step.setStyleSheet("color: #abb2bf; font-weight: 600; font-size: 11px;")
                top_row.addWidget(lbl_step)

                if is_ret:
                    score_str = f"Score: {score:.3f}" if isinstance(score, (int, float)) else "Top Match"
                    lbl_ret = QLabel(f"🟢 RECUPERADO ({score_str})", card)
                    lbl_ret.setStyleSheet(
                        "background-color: rgba(152, 195, 121, 0.2); color: #98c379; "
                        "font-size: 9px; font-weight: 800; border-radius: 3px; padding: 2px 6px;"
                    )
                    top_row.addWidget(lbl_ret)

                top_row.addStretch(1)
                c_layout.addLayout(top_row)

                body_lbl = QLabel(mem.get("text", ""), card)
                body_lbl.setWordWrap(True)
                body_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
                body_lbl.setStyleSheet("color: #abb2bf; font-size: 11px;")
                c_layout.addWidget(body_lbl)

                if mem.get("vector_sample"):
                    v_str = ", ".join(f"{x:.3f}" for x in mem["vector_sample"][:6])
                    v_lbl = QLabel(f"Vector sample ({mem.get('vector_dim', '?')}d): [{v_str}, ...]", card)
                    v_lbl.setStyleSheet("color: #5c6370; font-size: 10px; font-family: monospace;")
                    c_layout.addWidget(v_lbl)

                inner_layout.addWidget(card)

        inner_layout.addStretch(1)
        scroll.setWidget(inner)
        layout.addWidget(scroll)
        return container

    def _build_footer_stats(self) -> str:
        lines = self.content_text.count("\n") + 1
        chars = len(self.content_text)
        size_kb = round(chars / 1024.0, 1)
        return f"Total: {lines} líneas · {chars} caracteres (~{size_kb} KB) · Modo Solo Lectura"

    def _copy_to_clipboard(self) -> None:
        clipboard = QApplication.clipboard()
        clipboard.setText(self.content_text)
        self.btn_copy.setText("✓ ¡Copiado!")
        self.btn_copy.setStyleSheet("color: #98c379; border-color: #98c379;")

    def _save_to_disk(self) -> None:
        default_ext = "md" if self.filename.endswith(".md") else "txt"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar Representación de Memoria",
            self.filename,
            f"Archivos (*.{default_ext});;Todos los archivos (*.*)",
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self.content_text)
                self.btn_save.setText("✓ Guardado")
            except Exception as e:
                self.btn_save.setText("Error al guardar")


# ==============================================================================
# 2. PANEL PRINCIPAL DE REPRESENTACIÓN (REPRESENTATION PANEL)
# ==============================================================================
class RepresentationPanel(QWidget):
    """Panel que visualiza de forma consistente cómo el modelo/agente almacena la información:
    - Agente Aleatorio: Indicador de control sin memoria interna (Markoviano).
    - Agente Historial Clásico: Representación de archivo interactivo (historial_conversacion.txt)
      que puede ser presionado para visualizarse en su totalidad.
    - Agente RAG: Representación de almacén vectorial (almacen_vectorial.idx) con fragmentos
      indexados, consulta de similitud y explorador completo.
    """

    def __init__(
        self,
        chat_controller: ChatController | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.chat_controller = chat_controller
        self.setObjectName("RepresentationPanel")

        self.current_rep_data: dict[str, Any] | None = None

        self._build_ui()

        # Cargar representación inicial si el controlador está presente
        if self.chat_controller:
            self.refresh_representation()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(14, 12, 14, 10)
        root_layout.setSpacing(8)

        # 1. Cabecera del Panel (con el mismo estilo visual unificado que MapPanel)
        top_bar = QWidget(self)
        top_bar.setObjectName("RepresentationTopBar")
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(0, 0, 0, 0)
        top_bar_layout.setSpacing(8)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        self.title_label = QLabel("REPRESENTACIÓN DE MEMORIA", top_bar)
        self.title_label.setObjectName("RepresentationTitleLabel")
        self.title_label.setStyleSheet("color: #abb2bf; font-size: 11px; font-weight: 700; letter-spacing: 1px;")

        self.agent_badge_label = QLabel("🎲 Sin Memoria (Aleatorio)", top_bar)
        self.agent_badge_label.setObjectName("RepresentationBadgeLabel")
        self.agent_badge_label.setStyleSheet("color: #7f848e; font-size: 11px; font-weight: 600;")

        title_box.addWidget(self.title_label)
        title_box.addWidget(self.agent_badge_label)
        top_bar_layout.addLayout(title_box, stretch=1)

        # Botón para refrescar
        self.btn_refresh = QPushButton("🔄", top_bar)
        self.btn_refresh.setObjectName("RepresentationRefreshBtn")
        self.btn_refresh.setToolTip("Refrescar representación interna")
        self.btn_refresh.setFixedSize(26, 26)
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.setStyleSheet(
            """
            QPushButton#RepresentationRefreshBtn {
                background-color: #21252b;
                color: #abb2bf;
                border: 1px solid #3e4451;
                border-radius: 5px;
                font-size: 12px;
            }
            QPushButton#RepresentationRefreshBtn:hover {
                background-color: #2c313a;
                color: #ffffff;
                border-color: #61afef;
            }
            """
        )
        self.btn_refresh.clicked.connect(self.refresh_representation)

        # Botón principal para inspeccionar en su totalidad
        self.btn_inspect_full = QPushButton("👁️ Ver Todo", top_bar)
        self.btn_inspect_full.setObjectName("RepresentationInspectBtn")
        self.btn_inspect_full.setToolTip("Abrir y ver en su totalidad el archivo o almacén")
        self.btn_inspect_full.setFixedHeight(26)
        self.btn_inspect_full.setCursor(Qt.PointingHandCursor)
        self.btn_inspect_full.setStyleSheet(
            """
            QPushButton#RepresentationInspectBtn {
                background-color: #21252b;
                color: #61afef;
                border: 1px solid #3e4451;
                border-radius: 5px;
                font-size: 11px;
                font-weight: 700;
                padding: 0 8px;
            }
            QPushButton#RepresentationInspectBtn:hover {
                background-color: #2c313a;
                color: #ffffff;
                border-color: #61afef;
            }
            QPushButton#RepresentationInspectBtn:disabled {
                color: #5c6370;
                border-color: #2c313a;
            }
            """
        )
        self.btn_inspect_full.clicked.connect(self.open_full_representation)
        self.btn_inspect_full.setEnabled(False)

        top_bar_layout.addWidget(self.btn_inspect_full)
        top_bar_layout.addWidget(self.btn_refresh)
        root_layout.addWidget(top_bar)

        # 2. Scroll Area con el contenido interactivo
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("background-color: transparent;")

        self.content_container = QWidget()
        self.content_container.setObjectName("RepresentationContent")
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 4, 0, 0)
        self.content_layout.setSpacing(10)

        self.scroll_area.setWidget(self.content_container)
        root_layout.addWidget(self.scroll_area, stretch=1)

        # Render inicial por defecto (vacío / aleatorio)
        self._render_empty_state()

    # --------------------------------------------------------------------------
    # Sincronización y Actualización de Estado
    # --------------------------------------------------------------------------
    def refresh_representation(self) -> None:
        """Obtiene la representación más reciente desde el agente del chat controller."""
        if not self.chat_controller:
            return

        if hasattr(self.chat_controller, "get_agent_representation"):
            rep = self.chat_controller.get_agent_representation()
        elif hasattr(self.chat_controller, "agente") and self.chat_controller.agente:
            rep = self.chat_controller.agente.get_representation()
        else:
            rep = None

        self.set_representation(rep)

    def set_representation(self, rep_data: dict[str, Any] | None) -> None:
        """Recibe y visualiza la estructura y estado de memoria de cualquier agente."""
        self.current_rep_data = rep_data

        # Limpiar contenedor previo
        while self.content_layout.count() > 0:
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not rep_data or rep_data.get("type") == "none" or rep_data.get("agent_type") == "random":
            self.agent_badge_label.setText("🎲 Sin Memoria (Aleatorio)")
            self.agent_badge_label.setStyleSheet("color: #7f848e; font-size: 11px; font-weight: 600;")
            self.btn_inspect_full.setEnabled(False)
            self._render_empty_state()
            return

        agent_type = rep_data.get("agent_type") or rep_data.get("type")
        rep_type = rep_data.get("type")

        if agent_type == "classic_memory" or rep_type in ("classic_memory", "markdown"):
            self.agent_badge_label.setText("📜 Historial Clásico (LangChain)")
            self.agent_badge_label.setStyleSheet("color: #61afef; font-size: 11px; font-weight: 600;")
            self.btn_inspect_full.setEnabled(True)
            self._render_classic_memory_state(rep_data)
        elif agent_type == "rag_memory" or rep_type == "rag":
            self.agent_badge_label.setText("🧠 Memoria Avanzada (RAG Vectorial)")
            self.agent_badge_label.setStyleSheet("color: #98c379; font-size: 11px; font-weight: 600;")
            self.btn_inspect_full.setEnabled(True)
            self._render_rag_memory_state(rep_data)
        else:
            # Fallback genérico para otros tipos
            self.agent_badge_label.setText(f"⚙️ {rep_data.get('name', 'Modelo Activo')}")
            self.agent_badge_label.setStyleSheet("color: #e5c07b; font-size: 11px; font-weight: 600;")
            self.btn_inspect_full.setEnabled(True)
            self._render_generic_state(rep_data)

    def open_full_representation(self) -> None:
        """Abre el diálogo modal con el archivo o almacén completo."""
        if not self.current_rep_data:
            return

        filename = self.current_rep_data.get("filename")
        if not filename:
            if self.current_rep_data.get("type") == "rag":
                filename = "almacen_vectorial.idx"
            else:
                filename = "historial_conversacion.txt"

        title = self.current_rep_data.get("title", "Representación de Memoria")
        content_text = (
            self.current_rep_data.get("plain_text")
            or self.current_rep_data.get("markdown")
            or json.dumps(self.current_rep_data, indent=2, ensure_ascii=False)
        )
        subtitle = self.current_rep_data.get("description", "")

        dialog = RepresentationViewerDialog(
            title=title,
            filename=filename,
            content_text=content_text,
            subtitle=subtitle,
            details_data=self.current_rep_data,
            parent=self.window(),
        )
        dialog.exec()

    # --------------------------------------------------------------------------
    # 1. ESTADO RANDOM / CONTROL SIN MEMORIA
    # --------------------------------------------------------------------------
    def _render_empty_state(self) -> None:
        card = QFrame(self.content_container)
        card.setObjectName("RepresentationEmptyCard")
        card.setStyleSheet(
            """
            QFrame#RepresentationEmptyCard {
                background-color: #21252b;
                border: 1px dashed #3e4451;
                border-radius: 8px;
                padding: 16px;
            }
            """
        )
        layout = QVBoxLayout(card)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignCenter)

        icon = QLabel("🎲", card)
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("font-size: 32px;")
        layout.addWidget(icon)

        title = QLabel("Sin Memoria Interna", card)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #e5c07b; font-weight: 700; font-size: 13px;")
        layout.addWidget(title)

        tag = QLabel("MODO CONTROL MARKOVIANO (BASELINE)", card)
        tag.setAlignment(Qt.AlignCenter)
        tag.setStyleSheet(
            "color: #7f848e; font-size: 9px; font-weight: 800; letter-spacing: 1px; "
            "background-color: #1a1d21; border-radius: 4px; padding: 3px 8px;"
        )
        layout.addWidget(tag)

        desc = QLabel(
            "El Agente Aleatorio opera sin memoria episódica ni representaciones de estado. "
            "En cada turno toma decisiones estocásticas uniformes sobre las opciones admisibles.",
            card,
        )
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        desc.setStyleSheet("color: #7f848e; font-size: 11px; line-height: 1.4;")
        layout.addWidget(desc)

        # Chips de estadísticas cero
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(6)
        stats_layout.setAlignment(Qt.AlignCenter)

        for label, val in [("Elementos", "0"), ("Memoria", "0 B"), ("Ventana", "0 t")]:
            chip = QLabel(f"{label}: {val}", card)
            chip.setStyleSheet("background-color: #1a1d21; color: #5c6370; font-size: 10px; border-radius: 4px; padding: 2px 6px;")
            stats_layout.addWidget(chip)

        layout.addLayout(stats_layout)
        self.content_layout.addWidget(card)
        self.content_layout.addStretch(1)

    # --------------------------------------------------------------------------
    # 2. ESTADO AGENTE HISTORIAL CLÁSICO (ARCHIVO CLICKEABLE)
    # --------------------------------------------------------------------------
    def _render_classic_memory_state(self, rep: dict[str, Any]) -> None:
        filename = rep.get("filename", "historial_conversacion.txt")
        total_turns = rep.get("total_turns", 0)
        total_msgs = rep.get("total_messages", 0)
        window = rep.get("window_turns", 0)
        stats = rep.get("stats", {})
        size_bytes = stats.get("memory_size_bytes", 0)
        size_str = f"{size_bytes} B" if size_bytes < 1024 else f"{size_bytes / 1024.0:.1f} KB"

        # A. TARJETA VISUAL DEL ARCHIVO (Clickeable para ver en su totalidad)
        file_card = QFrame(self.content_container)
        file_card.setObjectName("RepresentationFileCard")
        file_card.setCursor(Qt.PointingHandCursor)
        file_card.setStyleSheet(
            """
            QFrame#RepresentationFileCard {
                background-color: #21252b;
                border: 1px solid #3e4451;
                border-radius: 8px;
                padding: 12px;
            }
            QFrame#RepresentationFileCard:hover {
                background-color: #282c34;
                border: 1px solid #61afef;
            }
            """
        )

        card_layout = QVBoxLayout(file_card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(8)

        # Fila superior: Icono + Nombre del archivo + Botón Abrir
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        file_icon = QLabel("📄", file_card)
        file_icon.setStyleSheet("font-size: 26px;")
        top_row.addWidget(file_icon)

        file_info = QVBoxLayout()
        file_info.setSpacing(2)
        lbl_fname = QLabel(filename, file_card)
        lbl_fname.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 700;")
        lbl_fdesc = QLabel("Buffer secuencial de contexto (LangChain)", file_card)
        lbl_fdesc.setStyleSheet("color: #7f848e; font-size: 10px;")
        file_info.addWidget(lbl_fname)
        file_info.addWidget(lbl_fdesc)
        top_row.addLayout(file_info, stretch=1)

        btn_open = QPushButton("👁️ Abrir", file_card)
        btn_open.setCursor(Qt.PointingHandCursor)
        btn_open.setStyleSheet(
            """
            QPushButton {
                background-color: #61afef;
                color: #1e2227;
                font-weight: 700;
                font-size: 11px;
                border-radius: 4px;
                padding: 4px 10px;
                border: none;
            }
            QPushButton:hover {
                background-color: #5294e2;
            }
            """
        )
        btn_open.clicked.connect(self.open_full_representation)
        top_row.addWidget(btn_open)
        card_layout.addLayout(top_row)

        # Fila de metadatos del archivo
        meta_row = QHBoxLayout()
        meta_row.setSpacing(6)

        chips = [
            f"📦 {size_str}",
            f"💬 {total_turns} turnos ({total_msgs} msgs)",
            f"🪟 Ventana: {window} turnos",
        ]
        for c in chips:
            lbl_chip = QLabel(c, file_card)
            lbl_chip.setStyleSheet(
                "background-color: #1a1d21; color: #abb2bf; font-size: 10px; "
                "font-weight: 600; border-radius: 4px; padding: 3px 6px;"
            )
            meta_row.addWidget(lbl_chip)

        meta_row.addStretch(1)
        card_layout.addLayout(meta_row)

        # Al hacer clic en cualquier parte de la tarjeta también se abre
        file_card.mousePressEvent = lambda event: self.open_full_representation()

        self.content_layout.addWidget(file_card)

        # B. PREVISUALIZACIÓN DEL BUFFER (ÚLTIMOS TURNOS)
        lbl_preview_title = QLabel("PREVISUALIZACIÓN DEL BUFFER (ÚLTIMOS TURNOS)", self.content_container)
        lbl_preview_title.setStyleSheet("color: #7f848e; font-size: 10px; font-weight: 700; letter-spacing: 0.5px;")
        self.content_layout.addWidget(lbl_preview_title)

        preview_frame = QFrame(self.content_container)
        preview_frame.setStyleSheet(
            """
            QFrame {
                background-color: #1e2227;
                border: 1px solid #3e4451;
                border-radius: 6px;
                padding: 8px;
            }
            """
        )
        p_layout = QVBoxLayout(preview_frame)
        p_layout.setContentsMargins(8, 8, 8, 8)
        p_layout.setSpacing(6)

        turns = rep.get("turns", [])
        if not turns:
            empty_p = QLabel("(Buffer vacío. Inicia una partida o ejecuta una acción para comenzar a registrar turnos).", preview_frame)
            empty_p.setStyleSheet("color: #5c6370; font-size: 11px; font-style: italic;")
            p_layout.addWidget(empty_p)
        else:
            # Mostrar los últimos 2 turnos como muestra rápida
            sample_turns = turns[-2:]
            for t in sample_turns:
                t_idx = t.get("turn", 1)
                is_act = t.get("is_active", True)
                tag = "🟢 ACTIVO" if is_act else "⚪ ARCHIVADO"
                tag_color = "#98c379" if is_act else "#5c6370"

                t_header = QLabel(f"Turno {t_idx} — {tag}", preview_frame)
                t_header.setStyleSheet(f"color: {tag_color}; font-weight: 700; font-size: 10px;")
                p_layout.addWidget(t_header)

                obs_raw = t.get("observation", "")
                obs_snip = obs_raw[:120].strip() + ("..." if len(obs_raw) > 120 else "")
                lbl_obs = QLabel(f"OBS: {obs_snip}", preview_frame)
                lbl_obs.setWordWrap(True)
                lbl_obs.setStyleSheet("color: #abb2bf; font-size: 10px; font-family: monospace;")
                p_layout.addWidget(lbl_obs)

                act_raw = t.get("action", "")
                lbl_act = QLabel(f"ACC: {act_raw}", preview_frame)
                lbl_act.setStyleSheet("color: #e5c07b; font-size: 10px; font-weight: 700; font-family: monospace;")
                p_layout.addWidget(lbl_act)

        # Enlace rápido al final para ver todo
        btn_full_link = QPushButton("👉 Apretar aquí para ver el archivo completo...", preview_frame)
        btn_full_link.setCursor(Qt.PointingHandCursor)
        btn_full_link.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                color: #61afef;
                font-size: 11px;
                font-weight: 600;
                text-align: left;
                border: none;
                padding-top: 4px;
            }
            QPushButton:hover {
                text-decoration: underline;
                color: #ffffff;
            }
            """
        )
        btn_full_link.clicked.connect(self.open_full_representation)
        p_layout.addWidget(btn_full_link)

        self.content_layout.addWidget(preview_frame)
        self.content_layout.addStretch(1)

    # --------------------------------------------------------------------------
    # 3. ESTADO AGENTE RAG MEMORY (ALMACÉN VECTORIAL)
    # --------------------------------------------------------------------------
    def _render_rag_memory_state(self, rep: dict[str, Any]) -> None:
        filename = rep.get("filename", "almacen_vectorial.idx")
        total_memories = rep.get("total_memories", 0)
        vector_dim = rep.get("vector_dimension", 128)
        embedding_model = rep.get("embedding_model", "embeddings")
        top_k = rep.get("top_k", 3)
        last_query = rep.get("last_query", "")
        last_retrieved = rep.get("last_retrieved", [])
        memories = rep.get("memories", [])

        # A. TARJETA VISUAL DEL ALMACÉN VECTORIAL (Clickeable)
        store_card = QFrame(self.content_container)
        store_card.setObjectName("RepresentationStoreCard")
        store_card.setCursor(Qt.PointingHandCursor)
        store_card.setStyleSheet(
            """
            QFrame#RepresentationStoreCard {
                background-color: #21252b;
                border: 1px solid #3e4451;
                border-radius: 8px;
                padding: 12px;
            }
            QFrame#RepresentationStoreCard:hover {
                background-color: #282c34;
                border: 1px solid #98c379;
            }
            """
        )

        card_layout = QVBoxLayout(store_card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(8)

        # Fila superior: Icono + Nombre + Botón Explorar
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        store_icon = QLabel("🗄️", store_card)
        store_icon.setStyleSheet("font-size: 26px;")
        top_row.addWidget(store_icon)

        store_info = QVBoxLayout()
        store_info.setSpacing(2)
        lbl_sname = QLabel(filename, store_card)
        lbl_sname.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 700;")
        lbl_sdesc = QLabel("Base de Conocimiento Vectorial · LangChain", store_card)
        lbl_sdesc.setStyleSheet("color: #7f848e; font-size: 10px;")
        store_info.addWidget(lbl_sname)
        store_info.addWidget(lbl_sdesc)
        top_row.addLayout(store_info, stretch=1)

        btn_explore = QPushButton("👁️ Explorar", store_card)
        btn_explore.setCursor(Qt.PointingHandCursor)
        btn_explore.setStyleSheet(
            """
            QPushButton {
                background-color: #98c379;
                color: #1e2227;
                font-weight: 700;
                font-size: 11px;
                border-radius: 4px;
                padding: 4px 10px;
                border: none;
            }
            QPushButton:hover {
                background-color: #87b368;
            }
            """
        )
        btn_explore.clicked.connect(self.open_full_representation)
        top_row.addWidget(btn_explore)
        card_layout.addLayout(top_row)

        # Fila de metadatos de vectores
        meta_row = QHBoxLayout()
        meta_row.setSpacing(6)

        chips = [
            f"🔢 {total_memories} fragmentos",
            f"📐 {vector_dim}d",
            f"🎯 Top-k: {top_k}",
        ]
        for c in chips:
            lbl_chip = QLabel(c, store_card)
            lbl_chip.setStyleSheet(
                "background-color: #1a1d21; color: #abb2bf; font-size: 10px; "
                "font-weight: 600; border-radius: 4px; padding: 3px 6px;"
            )
            meta_row.addWidget(lbl_chip)

        meta_row.addStretch(1)
        card_layout.addLayout(meta_row)

        store_card.mousePressEvent = lambda event: self.open_full_representation()
        self.content_layout.addWidget(store_card)

        # B. BANNER DE ÚLTIMA CONSULTA / RECUPERACIÓN RAG
        if last_query:
            query_box = QFrame(self.content_container)
            query_box.setStyleSheet(
                """
                QFrame {
                    background-color: #1e2227;
                    border: 1px solid #3e4451;
                    border-radius: 6px;
                    padding: 8px;
                }
                """
            )
            q_layout = QVBoxLayout(query_box)
            q_layout.setContentsMargins(8, 8, 8, 8)
            q_layout.setSpacing(4)

            q_head = QLabel("🔍 ÚLTIMA CONSULTA SEMÁNTICA", query_box)
            q_head.setStyleSheet("color: #61afef; font-size: 9px; font-weight: 800; letter-spacing: 0.5px;")
            q_layout.addWidget(q_head)

            q_text = QLabel(f'"{last_query[:90]}..."' if len(last_query) > 90 else f'"{last_query}"', query_box)
            q_text.setWordWrap(True)
            q_text.setStyleSheet("color: #abb2bf; font-size: 11px; font-style: italic;")
            q_layout.addWidget(q_text)

            ret_count = len(last_retrieved)
            lbl_ret_count = QLabel(f"🎯 {ret_count} fragmentos recuperados afines en este turno", query_box)
            lbl_ret_count.setStyleSheet("color: #98c379; font-size: 10px; font-weight: 600;")
            q_layout.addWidget(lbl_ret_count)

            self.content_layout.addWidget(query_box)

        # C. LISTA DE FRAGMENTOS / CHUNKS INDEXADOS (Muestra interactiva)
        lbl_chunks_title = QLabel(f"FRAGMENTOS INDEXADOS ({min(5, len(memories))} de {len(memories)})", self.content_container)
        lbl_chunks_title.setStyleSheet("color: #7f848e; font-size: 10px; font-weight: 700; letter-spacing: 0.5px;")
        self.content_layout.addWidget(lbl_chunks_title)

        if not memories:
            empty_lbl = QLabel("(Almacén vacío. Ejecuta acciones para almacenar recuerdos vectoriales).", self.content_container)
            empty_lbl.setStyleSheet("color: #5c6370; font-size: 11px; font-style: italic;")
            self.content_layout.addWidget(empty_lbl)
        else:
            # Mostrar los últimos 4 fragmentos
            sample_mems = memories[-4:]
            for mem in sample_mems:
                c_card = QFrame(self.content_container)
                c_card.setCursor(Qt.PointingHandCursor)
                c_card.setStyleSheet(
                    """
                    QFrame {
                        background-color: #21252b;
                        border: 1px solid #3e4451;
                        border-radius: 6px;
                    }
                    QFrame:hover {
                        border-color: #98c379;
                        background-color: #282c34;
                    }
                    """
                )
                c_layout = QVBoxLayout(c_card)
                c_layout.setContentsMargins(8, 6, 8, 6)
                c_layout.setSpacing(3)

                c_top = QHBoxLayout()
                cat = mem.get("category", "obs").upper()
                step = mem.get("step", 0)
                is_ret = mem.get("is_retrieved", False)

                lbl_cat = QLabel(f"[{cat[:3]}] P{step}", c_card)
                lbl_cat.setStyleSheet(
                    f"color: {'#61afef' if 'OBS' in cat else '#c678dd'}; "
                    "font-size: 10px; font-weight: 700;"
                )
                c_top.addWidget(lbl_cat)

                if is_ret:
                    lbl_top = QLabel("🟢 Top Match", c_card)
                    lbl_top.setStyleSheet(
                        "background-color: rgba(152, 195, 121, 0.2); color: #98c379; "
                        "font-size: 9px; font-weight: 800; border-radius: 3px; padding: 1px 4px;"
                    )
                    c_top.addWidget(lbl_top)

                c_top.addStretch(1)
                c_layout.addLayout(c_top)

                t_snip = mem.get("text", "")[:95].strip() + ("..." if len(mem.get("text", "")) > 95 else "")
                lbl_snip = QLabel(t_snip, c_card)
                lbl_snip.setWordWrap(True)
                lbl_snip.setStyleSheet("color: #abb2bf; font-size: 10px;")
                c_layout.addWidget(lbl_snip)

                c_card.mousePressEvent = lambda event: self.open_full_representation()
                self.content_layout.addWidget(c_card)

        # Enlace para abrir visor completo
        btn_full_rag = QPushButton("👉 Apretar aquí para explorar el almacén completo...", self.content_container)
        btn_full_rag.setCursor(Qt.PointingHandCursor)
        btn_full_rag.setStyleSheet(
            """
            QPushButton {
                background-color: transparent;
                color: #98c379;
                font-size: 11px;
                font-weight: 600;
                text-align: left;
                border: none;
                padding-top: 4px;
            }
            QPushButton:hover {
                text-decoration: underline;
                color: #ffffff;
            }
            """
        )
        btn_full_rag.clicked.connect(self.open_full_representation)
        self.content_layout.addWidget(btn_full_rag)

        self.content_layout.addStretch(1)

    # --------------------------------------------------------------------------
    # 4. ESTADO GENÉRICO DE RESPALDO
    # --------------------------------------------------------------------------
    def _render_generic_state(self, rep: dict[str, Any]) -> None:
        title = rep.get("title", "Representación")
        card = QFrame(self.content_container)
        card.setStyleSheet(
            """
            QFrame {
                background-color: #21252b;
                border: 1px solid #3e4451;
                border-radius: 8px;
                padding: 12px;
            }
            """
        )
        layout = QVBoxLayout(card)
        lbl = QLabel(title, card)
        lbl.setStyleSheet("color: #ffffff; font-weight: 700; font-size: 12px;")
        layout.addWidget(lbl)

        btn = QPushButton("👁️ Ver representación completa", card)
        btn.clicked.connect(self.open_full_representation)
        layout.addWidget(btn)

        self.content_layout.addWidget(card)
        self.content_layout.addStretch(1)
