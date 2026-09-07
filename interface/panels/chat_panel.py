from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from controllers.chat_controller import ChatController, ChatMessage


from typing import Callable


class BubbleWidget(QFrame):
    def __init__(self, message: ChatMessage, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        role = message.role.lower()
        self.setObjectName("UserBubble" if role == "user" else "AgentBubble")

        text_label = QLabel(message.text, self)
        text_label.setWordWrap(True)
        text_label.setObjectName("UserText" if role == "user" else "AgentText")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.addWidget(text_label)


class ChatPanel(QWidget):
    def __init__(
        self,
        controller: ChatController,
        on_configure: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.controller = controller
        self.on_configure = on_configure
        self.setObjectName("RightPanel")

        root_layout = QVBoxLayout(self)
        # Keep 1px free on the left so the panel border is not covered by child widgets.
        root_layout.setContentsMargins(1, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_header())
        root_layout.addWidget(self._build_messages_area(), stretch=1)
        root_layout.addWidget(self._build_input_area())

        self.controller.state_changed.connect(self.refresh_messages)
        self.refresh_messages()

    def _build_header(self) -> QWidget:
        header = QWidget(self)
        header.setObjectName("ChatHeader")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(25, 15, 25, 15)

        model_info = QHBoxLayout()
        model_info.setSpacing(10)

        status_dot = QLabel(header)
        status_dot.setFixedSize(10, 10)
        dot_color = "#59ff93" if self.controller.is_online else "#5c6370"
        status_dot.setStyleSheet(f"background-color: {dot_color}; border-radius: 5px;")

        model_label = QLabel(f"{self.controller.model_name}", header)
        model_label.setObjectName("ModelLabel")
        model_glow = QGraphicsDropShadowEffect(model_label)
        model_glow.setBlurRadius(20)
        model_glow.setOffset(0, 0)
        model_glow.setColor(QColor("#59e8ff"))

        if self.controller.is_online:
            status_dot.setGraphicsEffect(model_glow)


        model_info.addWidget(status_dot)
        model_info.addWidget(model_label)
        model_info.addStretch()

        controls = QHBoxLayout()
        controls.setSpacing(8)

        config_btn = self._header_button("CONFIG")
        reset_btn = self._header_button("RESET")
        next_btn = self._header_button("NEXT-STEP")

        if self.on_configure:
            config_btn.clicked.connect(self.on_configure)

        reset_btn.clicked.connect(self.controller.reset_conversation)
        next_btn.clicked.connect(self.controller.next_step)

        controls.addWidget(config_btn)
        controls.addWidget(next_btn)
        controls.addWidget(reset_btn)

        layout.addLayout(model_info)
        layout.addLayout(controls)
        return header

    def _header_button(self, text: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("HeaderControl")
        button.setCursor(Qt.PointingHandCursor)
        return button

    def _build_messages_area(self) -> QScrollArea:
        self.messages_container = QWidget(self)
        self.messages_container.setObjectName("MessagesContainer")
        self.messages_container.setAutoFillBackground(False)
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(25, 25, 25, 25)
        self.messages_layout.setSpacing(15)
        self.messages_layout.addStretch()

        area = QScrollArea(self)
        area.setObjectName("MessagesArea")
        area.setWidgetResizable(True)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        area.setWidget(self.messages_container)
        area.viewport().setAutoFillBackground(False)
        self.messages_area = area
        self.messages_area.verticalScrollBar().rangeChanged.connect(self._scroll_to_bottom)
        return area

    def _scroll_to_bottom(self) -> None:
        scrollbar = self.messages_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _build_input_area(self) -> QWidget:
        input_area = QWidget(self)
        input_area.setObjectName("ChatInputArea")
        layout = QHBoxLayout(input_area)
        layout.setContentsMargins(25, 15, 25, 15)
        layout.setSpacing(15)

        disabled_input = QLineEdit("Chat deshabilitado... (Modo mapa-agente activo)", input_area)
        disabled_input.setObjectName("DisabledInput")
        disabled_input.setReadOnly(True)
        disabled_input.setEnabled(False)

        send_icon = QLabel(">", input_area)
        send_icon.setObjectName("SendIcon")
        send_icon.setFixedWidth(18)
        send_icon.setAlignment(Qt.AlignCenter)

        layout.addWidget(disabled_input)
        layout.addWidget(send_icon)
        return input_area

    def refresh_messages(self) -> None:
        while self.messages_layout.count() > 1:
            item = self.messages_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for message in self.controller.messages:
            row = QWidget(self.messages_container)
            row.setObjectName("ChatMessageRow")
            row.setAttribute(Qt.WA_StyledBackground, True)
            row.setStyleSheet("background-color: transparent;")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)

            bubble = BubbleWidget(message, row)
            bubble.setMaximumWidth(460)
            bubble.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

            if message.role.lower() == "user":
                row_layout.addStretch()
                row_layout.addWidget(bubble)
            else:
                row_layout.addWidget(bubble)
                row_layout.addStretch()

            self.messages_layout.insertWidget(self.messages_layout.count() - 1, row)

        QTimer.singleShot(0, self._scroll_to_bottom)


