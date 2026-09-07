from __future__ import annotations

import math
from typing import Any

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from controllers.graph_controller import GraphController


CARD_WIDTH = 94.0
CARD_HEIGHT = 58.0
STEP_X = 145.0
STEP_Y = 105.0


class MapPanel(QWidget):
    """Panel visual avanzado e interactivo que representa el estado del mundo de TextWorld:
    habitaciones, jugador, conexiones, puertas (abierta/cerrada/bloqueada),
    contenedores, superficies, objetos sueltos, inventario y leyenda.
    """

    def __init__(self, controller: GraphController, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.controller = controller
        self.setObjectName("MapPanel")
        self.setMouseTracking(True)

        # Estado del mundo
        self._primitives: dict[str, Any] = controller.get_primitives()
        self._world_state: dict[str, Any] = self._primitives.get("world_state", {})

        # Estado de navegación (Pan & Zoom)
        self._pan_x: float = 0.0
        self._pan_y: float = 0.0
        self._zoom: float = 1.0
        self._is_panning: bool = False
        self._last_mouse_pos: QPointF | None = None
        self._initial_fit_done: bool = False

        # Estado interactivo (Hover)
        self._hovered_room: dict[str, Any] | None = None
        self._hovered_door: dict[str, Any] | None = None

        # Construir HUD flotante
        self._build_hud()

    def _build_hud(self) -> None:
        """Construye las capas superpuestas de HUD (cabecera, controles de zoom e inventario)."""
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(14, 12, 14, 10)
        root_layout.setSpacing(0)

        # Top Bar: Título, ubicación actual y botones de zoom
        top_bar = QWidget(self)
        top_bar.setObjectName("MapTopBar")
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(0, 0, 0, 0)
        top_bar_layout.setSpacing(10)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        self.title_label = QLabel("MAPA DEL MUNDO", top_bar)
        self.title_label.setObjectName("MapLabel")

        self.location_label = QLabel("📍 Sin entorno activo", top_bar)
        self.location_label.setObjectName("MapLocationLabel")
        self.location_label.setStyleSheet("color: #61afef; font-size: 11px; font-weight: 600;")

        info_layout.addWidget(self.title_label)
        info_layout.addWidget(self.location_label)
        top_bar_layout.addLayout(info_layout, stretch=1)

        # Controles de navegación rápida
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)

        self.btn_zoom_in = QPushButton("+", top_bar)
        self.btn_zoom_in.setObjectName("MapZoomBtn")
        self.btn_zoom_in.setFixedSize(26, 26)
        self.btn_zoom_in.setToolTip("Acercar zoom")
        self.btn_zoom_in.setCursor(Qt.PointingHandCursor)
        self.btn_zoom_in.clicked.connect(self._zoom_in)

        self.btn_zoom_out = QPushButton("-", top_bar)
        self.btn_zoom_out.setObjectName("MapZoomBtn")
        self.btn_zoom_out.setFixedSize(26, 26)
        self.btn_zoom_out.setToolTip("Alejar zoom")
        self.btn_zoom_out.setCursor(Qt.PointingHandCursor)
        self.btn_zoom_out.clicked.connect(self._zoom_out)

        self.btn_fit = QPushButton("⛶", top_bar)
        self.btn_fit.setObjectName("MapZoomBtn")
        self.btn_fit.setFixedSize(26, 26)
        self.btn_fit.setToolTip("Centrar mapa y autoajustar")
        self.btn_fit.setCursor(Qt.PointingHandCursor)
        self.btn_fit.clicked.connect(self.auto_fit)

        btn_layout.addWidget(self.btn_zoom_in)
        btn_layout.addWidget(self.btn_zoom_out)
        btn_layout.addWidget(self.btn_fit)
        top_bar_layout.addLayout(btn_layout)

        root_layout.addWidget(top_bar)
        root_layout.addStretch(1)

        # Bottom HUD: Inventario y leyenda rápida
        self.bottom_hud = QWidget(self)
        self.bottom_hud.setObjectName("MapBottomHud")
        self.bottom_hud.setStyleSheet(
            "QWidget#MapBottomHud {"
            "  background-color: rgba(33, 37, 43, 0.92);"
            "  border: 1px solid #3e4451;"
            "  border-radius: 8px;"
            "  padding: 4px;"
            "}"
        )
        bottom_layout = QVBoxLayout(self.bottom_hud)
        bottom_layout.setContentsMargins(10, 6, 10, 6)
        bottom_layout.setSpacing(3)

        self.inventory_label = QLabel("🎒 Inventario: (vacío)", self.bottom_hud)
        self.inventory_label.setStyleSheet("color: #e5c07b; font-size: 11px; font-weight: 600;")

        self.legend_label = QLabel(
            "🔵 Jugador  •  🟢 Puerta abierta  •  🟠 Puerta cerrada  •  🔴 Bloqueada  •  📦 Contenedor  •  🗝️ Llave  •  🔹 Objeto",
            self.bottom_hud,
        )
        self.legend_label.setStyleSheet("color: #7f8899; font-size: 9.5px;")

        bottom_layout.addWidget(self.inventory_label)
        bottom_layout.addWidget(self.legend_label)

        root_layout.addWidget(self.bottom_hud)

    # ------------------ Actualización de Estado ------------------
    def set_primitives(self, primitives: dict[str, Any]) -> None:
        self._primitives = primitives
        self._world_state = primitives.get("world_state", {})
        self._update_hud_texts()

        # Si es la primera vez o cambia el mundo sustancialmente, autoajustar
        if not self._initial_fit_done or not self.controller.current_room:
            self.auto_fit()
            self._initial_fit_done = True

        self.update()

    def refresh_map(self) -> None:
        self.set_primitives(self.controller.get_primitives())

    def _update_hud_texts(self) -> None:
        curr_room = self.controller.current_room or "Desconocido"
        self.location_label.setText(f"📍 Sala actual: {curr_room}")

        inv = self.controller.player_inventory
        if inv:
            inv_str = ", ".join(inv)
            self.inventory_label.setText(f"🎒 Inventario ({len(inv)}): {inv_str}")
        else:
            self.inventory_label.setText("🎒 Inventario: (vacío)")

    # ------------------ Transformación de Coordenadas y Auto-Fit ------------------
    def auto_fit(self) -> None:
        """Centra y escala el grafo para que encaje de manera óptima en la vista."""
        grid_coords = self.controller.grid_coords
        if not grid_coords:
            self._pan_x = 0.0
            self._pan_y = 0.0
            self._zoom = 1.0
            self.update()
            return

        min_gx = min(c[0] for c in grid_coords.values())
        max_gx = max(c[0] for c in grid_coords.values())
        min_gy = min(c[1] for c in grid_coords.values())
        max_gy = max(c[1] for c in grid_coords.values())

        span_w = (max_gx - min_gx) * STEP_X + CARD_WIDTH + 80.0
        span_h = (max_gy - min_gy) * STEP_Y + CARD_HEIGHT + 130.0

        avail_w = max(100.0, self.width() * 0.9)
        avail_h = max(100.0, self.height() * 0.75)

        zoom_x = avail_w / span_w
        zoom_y = avail_h / span_h
        target_zoom = min(zoom_x, zoom_y, 1.2)
        self._zoom = max(0.4, min(1.5, target_zoom))

        center_gx = (min_gx + max_gx) / 2.0
        center_gy = (min_gy + max_gy) / 2.0

        self._pan_x = -center_gx * STEP_X * self._zoom
        self._pan_y = -center_gy * STEP_Y * self._zoom
        self.update()

    def _grid_to_canvas(self, gx: int, gy: int) -> tuple[float, float]:
        cx = self.width() / 2.0 + self._pan_x + gx * STEP_X * self._zoom
        cy = self.height() / 2.0 + self._pan_y + gy * STEP_Y * self._zoom
        return cx, cy

    def _zoom_in(self) -> None:
        self._zoom = min(2.5, self._zoom * 1.2)
        self.update()

    def _zoom_out(self) -> None:
        self._zoom = max(0.35, self._zoom / 1.2)
        self.update()

    # ------------------ Renderizado Principal (paintEvent) ------------------
    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        self._draw_dot_grid(painter)
        self._draw_connections(painter)
        self._draw_room_cards(painter)

    def _draw_dot_grid(self, painter: QPainter) -> None:
        painter.save()
        dot_color = QColor("#495061")
        dot_color.setAlpha(100)
        painter.setPen(Qt.NoPen)
        painter.setBrush(dot_color)

        spacing = max(16.0, 24.0 * self._zoom)
        offset_x = (self.width() / 2.0 + self._pan_x) % spacing
        offset_y = (self.height() / 2.0 + self._pan_y) % spacing

        x = offset_x
        while x < self.width():
            y = offset_y
            while y < self.height():
                painter.drawEllipse(QPointF(x, y), 1.2, 1.2)
                y += spacing
            x += spacing
        painter.restore()

    def _draw_connections(self, painter: QPainter) -> None:
        connections = self._world_state.get("connections", [])
        grid_coords = self.controller.grid_coords

        for conn in connections:
            r1, r2 = conn["r1"], conn["r2"]
            if r1 not in grid_coords or r2 not in grid_coords:
                continue

            gx1, gy1 = grid_coords[r1]
            gx2, gy2 = grid_coords[r2]
            p1 = QPointF(*self._grid_to_canvas(gx1, gy1))
            p2 = QPointF(*self._grid_to_canvas(gx2, gy2))

            is_door = conn.get("is_door", False)
            door_state = conn.get("door_state", "free")
            is_hovered = self._hovered_door == conn

            # Dibujar la línea del pasillo
            corridor_color = QColor("#525b6c") if not is_door else (
                QColor("#98c379") if door_state == "open" else (
                    QColor("#e06c75") if door_state == "locked" else QColor("#e5c07b")
                )
            )

            # Si es pasillo libre, dibujar línea base elegante
            painter.save()
            line_pen = QPen(QColor("#3e4656"), max(2.0, 3.0 * self._zoom))
            painter.setPen(line_pen)
            painter.drawLine(p1, p2)

            # Si hay una puerta, dibujar el umbral en el punto medio
            if is_door:
                mid_x = (p1.x() + p2.x()) / 2.0
                mid_y = (p1.y() + p2.y()) / 2.0
                dx = p2.x() - p1.x()
                dy = p2.y() - p1.y()

                # Halo al pasar el cursor sobre la puerta
                if is_hovered:
                    glow_color = QColor(corridor_color)
                    glow_color.setAlpha(120)
                    painter.setPen(QPen(glow_color, 8))
                    painter.drawEllipse(QPointF(mid_x, mid_y), 12 * self._zoom, 12 * self._zoom)

                # Orientación de la barra de umbral
                is_horizontal = abs(dx) > abs(dy)
                bar_w = (8.0 if is_horizontal else 22.0) * self._zoom
                bar_h = (22.0 if is_horizontal else 8.0) * self._zoom
                door_rect = QRectF(mid_x - bar_w / 2.0, mid_y - bar_h / 2.0, bar_w, bar_h)

                fill_color = QColor(corridor_color)
                fill_color.setAlpha(80 if door_state != "open" else 40)

                painter.setBrush(fill_color)
                painter.setPen(QPen(corridor_color, max(1.5, 2.0 * self._zoom)))
                painter.drawRoundedRect(door_rect, 3.0, 3.0)

                # Icono de candado / punto si está bloqueada
                if door_state == "locked":
                    painter.setBrush(QColor("#e06c75"))
                    painter.setPen(Qt.NoPen)
                    painter.drawEllipse(QPointF(mid_x, mid_y), 3.0 * self._zoom, 3.0 * self._zoom)
                elif door_state == "open":
                    # Espacio abierto en el centro
                    painter.setBrush(QColor("#1e2227"))
                    painter.setPen(Qt.NoPen)
                    inner_w = (4.0 if is_horizontal else 14.0) * self._zoom
                    inner_h = (14.0 if is_horizontal else 4.0) * self._zoom
                    painter.drawRect(QRectF(mid_x - inner_w / 2.0, mid_y - inner_h / 2.0, inner_w, inner_h))

            painter.restore()

    def _draw_room_cards(self, painter: QPainter) -> None:
        rooms = self._world_state.get("rooms", {})
        grid_coords = self.controller.grid_coords

        cw = CARD_WIDTH * self._zoom
        ch = CARD_HEIGHT * self._zoom
        radius = max(5.0, 8.0 * self._zoom)

        for room_name, rdata in rooms.items():
            if room_name not in grid_coords:
                continue

            gx, gy = grid_coords[room_name]
            cx, cy = self._grid_to_canvas(gx, gy)
            card_rect = QRectF(cx - cw / 2.0, cy - ch / 2.0, cw, ch)

            is_current = rdata.get("is_current", False)
            visited = rdata.get("visited", False)
            is_hovered = self._hovered_room == rdata

            painter.save()

            # 1. Halo exterior brillante para la sala actual o hovered
            if is_current:
                glow_path = QPainterPath()
                glow_path.addRoundedRect(card_rect.adjusted(-4, -4, 4, 4), radius + 2, radius + 2)
                painter.fillPath(glow_path, QColor(97, 175, 239, 70))
            elif is_hovered:
                glow_path = QPainterPath()
                glow_path.addRoundedRect(card_rect.adjusted(-3, -3, 3, 3), radius + 1, radius + 1)
                painter.fillPath(glow_path, QColor(152, 195, 121, 55))

            # 2. Fondo de la tarjeta (gradiente o sólido según estado)
            if is_current:
                grad = QLinearGradient(card_rect.topLeft(), card_rect.bottomLeft())
                grad.setColorAt(0.0, QColor("#1e374f"))
                grad.setColorAt(1.0, QColor("#142333"))
                painter.setBrush(grad)
                border_pen = QPen(QColor("#61afef"), max(2.0, 2.5 * self._zoom))
            elif visited:
                painter.setBrush(QColor("#282c34"))
                border_color = QColor("#98c379") if is_hovered else QColor("#4c5565")
                border_pen = QPen(border_color, max(1.2, 1.6 * self._zoom))
            else:
                # Niebla de exploración (sala conocida no visitada)
                bg_color = QColor("#1a1e24")
                bg_color.setAlpha(210)
                painter.setBrush(bg_color)
                border_pen = QPen(QColor("#3e4451"), max(1.0, 1.2 * self._zoom), Qt.DashLine)

            painter.setPen(border_pen)
            painter.drawRoundedRect(card_rect, radius, radius)

            # 3. Distintivo superior (Avatar del Jugador o indicador de estado)
            if is_current:
                badge_h = max(12.0, 14.0 * self._zoom)
                badge_w = max(40.0, 48.0 * self._zoom)
                badge_rect = QRectF(cx - badge_w / 2.0, card_rect.top() - badge_h / 2.0, badge_w, badge_h)

                painter.setBrush(QColor("#61afef"))
                painter.setPen(Qt.NoPen)
                painter.drawRoundedRect(badge_rect, badge_h / 2.0, badge_h / 2.0)

                painter.setPen(QColor("#1e2227"))
                font_badge = QFont()
                font_badge.setBold(True)
                font_badge.setPointSize(max(6, int(7.5 * self._zoom)))
                painter.setFont(font_badge)
                painter.drawText(badge_rect, Qt.AlignCenter, "👤")

            # 4. Nombre de la Sala
            name_font = QFont()
            name_font.setBold(is_current or visited)
            name_font.setPointSize(max(7, int(9.5 * self._zoom)))
            painter.setFont(name_font)

            name_color = QColor("#ffffff") if (is_current or visited) else QColor("#747d8c")
            painter.setPen(name_color)

            fm = QFontMetrics(name_font)
            available_text_w = int(cw - 10)
            elided_name = fm.elidedText(room_name, Qt.ElideRight, available_text_w)

            # Posición del texto del nombre
            text_y_offset = (card_rect.top() + 8 * self._zoom) if is_current else (card_rect.top() + 6 * self._zoom)
            title_rect = QRectF(card_rect.left() + 5, text_y_offset, cw - 10, max(14.0, 18.0 * self._zoom))
            painter.drawText(title_rect, Qt.AlignCenter, elided_name)

            # 5. Micro-Badges de contenido (Contenedores, Llaves, Objetos, Soportes)
            containers = rdata.get("containers", [])
            supporters = rdata.get("supporters", [])
            items = rdata.get("items", [])

            # Contar categorías de ítems
            keys_count = sum(1 for it in items if it.get("category") == "key")
            food_count = sum(1 for it in items if it.get("category") == "food")
            misc_count = sum(1 for it in items if it.get("category") not in {"key", "food"})

            badges: list[tuple[str, QColor, str]] = []
            if containers:
                # Color según si alguno está bloqueado, cerrado o abierto
                any_locked = any(c.get("is_locked") for c in containers)
                all_open = all(c.get("is_open") for c in containers)
                c_col = QColor("#e06c75") if any_locked else (QColor("#98c379") if all_open else QColor("#e5c07b"))
                badges.append(("📦", c_col, str(len(containers)) if len(containers) > 1 else ""))

            if supporters:
                badges.append(("🪑", QColor("#abb2bf"), str(len(supporters)) if len(supporters) > 1 else ""))

            if keys_count > 0:
                badges.append(("🗝️", QColor("#e5c07b"), str(keys_count) if keys_count > 1 else ""))

            if food_count > 0:
                badges.append(("🥪", QColor("#98c379"), str(food_count) if food_count > 1 else ""))

            if misc_count > 0:
                badges.append(("🔹", QColor("#56b6c2"), str(misc_count) if misc_count > 1 else ""))

            # Dibujar los badges en la fila inferior de la tarjeta
            if badges:
                badge_row_y = card_rect.bottom() - max(14.0, 18.0 * self._zoom)
                badge_font = QFont()
                badge_font.setPointSize(max(6, int(8.0 * self._zoom)))
                painter.setFont(badge_font)

                total_badges = len(badges)
                badge_spacing = max(18.0, 22.0 * self._zoom)
                start_bx = cx - ((total_badges - 1) * badge_spacing) / 2.0

                for i, (icon, col, count_txt) in enumerate(badges):
                    bx = start_bx + i * badge_spacing
                    painter.setPen(col)
                    txt = f"{icon}{count_txt}" if count_txt else icon
                    b_rect = QRectF(bx - 10, badge_row_y, 20, 14 * self._zoom)
                    painter.drawText(b_rect, Qt.AlignCenter, txt)

            painter.restore()

    # ------------------ Interacción del Ratón (Pan, Zoom, Hover) ------------------
    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() in (Qt.LeftButton, Qt.MiddleButton):
            self._is_panning = True
            self._last_mouse_pos = event.position()
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        curr_pos = event.position()

        # Si estamos arrastrando para mover el mapa
        if self._is_panning and self._last_mouse_pos is not None:
            dx = curr_pos.x() - self._last_mouse_pos.x()
            dy = curr_pos.y() - self._last_mouse_pos.y()
            self._pan_x += dx
            self._pan_y += dy
            self._last_mouse_pos = curr_pos
            self.update()
            return

        # Detección de Hover sobre salas o puertas
        room = self._room_at(curr_pos)
        door = self._door_at(curr_pos) if room is None else None

        if room != self._hovered_room or door != self._hovered_door:
            self._hovered_room = room
            self._hovered_door = door
            self.update()

            if room is not None:
                QToolTip.showText(
                    event.globalPosition().toPoint(),
                    self._build_room_tooltip(room),
                    self,
                )
            elif door is not None:
                QToolTip.showText(
                    event.globalPosition().toPoint(),
                    self._build_door_tooltip(door),
                    self,
                )
            else:
                QToolTip.hideText()

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        if event.button() in (Qt.LeftButton, Qt.MiddleButton):
            self._is_panning = False
            self.setCursor(Qt.ArrowCursor)
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event) -> None:  # noqa: N802
        delta = event.angleDelta().y()
        if delta == 0:
            return

        factor = 1.15 if delta > 0 else (1.0 / 1.15)
        old_zoom = self._zoom
        new_zoom = max(0.35, min(2.5, old_zoom * factor))

        # Mantener el punto bajo el cursor quieto
        cursor_x = event.position().x()
        cursor_y = event.position().y()

        # Posición antes del zoom respecto al centro del mapa
        wx = (cursor_x - self.width() / 2.0 - self._pan_x) / old_zoom
        wy = (cursor_y - self.height() / 2.0 - self._pan_y) / old_zoom

        self._zoom = new_zoom
        self._pan_x = cursor_x - self.width() / 2.0 - wx * new_zoom
        self._pan_y = cursor_y - self.height() / 2.0 - wy * new_zoom

        self.update()
        event.accept()

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        self.auto_fit()
        super().mouseDoubleClickEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        QToolTip.hideText()
        if self._hovered_room is not None or self._hovered_door is not None:
            self._hovered_room = None
            self._hovered_door = None
            self.update()
        super().leaveEvent(event)

    # ------------------ Detección de Objetos bajo el Cursor ------------------
    def _room_at(self, pos: QPointF) -> dict[str, Any] | None:
        rooms = self._world_state.get("rooms", {})
        grid_coords = self.controller.grid_coords

        cw = CARD_WIDTH * self._zoom
        ch = CARD_HEIGHT * self._zoom

        for room_name, rdata in rooms.items():
            if room_name not in grid_coords:
                continue
            gx, gy = grid_coords[room_name]
            cx, cy = self._grid_to_canvas(gx, gy)
            rect = QRectF(cx - cw / 2.0, cy - ch / 2.0, cw, ch)
            if rect.contains(pos):
                return rdata
        return None

    def _door_at(self, pos: QPointF) -> dict[str, Any] | None:
        connections = self._world_state.get("connections", [])
        grid_coords = self.controller.grid_coords

        for conn in connections:
            if not conn.get("is_door", False):
                continue
            r1, r2 = conn["r1"], conn["r2"]
            if r1 not in grid_coords or r2 not in grid_coords:
                continue

            gx1, gy1 = grid_coords[r1]
            gx2, gy2 = grid_coords[r2]
            p1 = QPointF(*self._grid_to_canvas(gx1, gy1))
            p2 = QPointF(*self._grid_to_canvas(gx2, gy2))

            mid_x = (p1.x() + p2.x()) / 2.0
            mid_y = (p1.y() + p2.y()) / 2.0

            dist = math.hypot(pos.x() - mid_x, pos.y() - mid_y)
            if dist <= max(12.0, 16.0 * self._zoom):
                return conn
        return None

    # ------------------ Construcción de Tooltips Enriquecidos ------------------
    def _build_room_tooltip(self, room_data: dict[str, Any]) -> str:
        name = room_data["name"]
        is_current = room_data.get("is_current", False)
        visited = room_data.get("visited", False)

        status_badge = (
            "<span style='color: #61afef; font-weight: bold;'>[SALA ACTUAL]</span>"
            if is_current
            else (
                "<span style='color: #98c379;'>[VISITADA]</span>"
                if visited
                else "<span style='color: #747d8c;'>[POR EXPLORAR]</span>"
            )
        )

        html = "<div style='font-family: sans-serif; font-size: 12px; color: #abb2bf; padding: 4px; min-width: 210px;'>"
        html += f"<div style='font-size: 14px; font-weight: bold; color: #ffffff;'>📍 {name} {status_badge}</div>"
        html += "<hr style='border: 0; border-top: 1px solid #3e4451; margin: 6px 0;'/>"

        # Contenedores
        containers = room_data.get("containers", [])
        if containers:
            html += "<div style='margin-bottom: 5px;'><b style='color: #e5c07b;'>📦 Contenedores:</b><ul style='margin: 3px 0 0 0; padding-left: 18px;'>"
            for c in containers:
                state_text = (
                    "🔓 abierta"
                    if c.get("is_open")
                    else ("🔐 bloqueada" if c.get("is_locked") else "🔒 cerrada")
                )
                items = c.get("items", [])
                inside_text = (
                    f" &rarr; contiene: <i>{', '.join(items)}</i>"
                    if items
                    else " &rarr; <i>(vacío)</i>"
                )
                key_text = f" [Llave: {c['matching_key']}]" if c.get("matching_key") else ""
                html += f"<li><b>{c['name']}</b> ({state_text}){key_text}{inside_text}</li>"
            html += "</ul></div>"

        # Superficies / Soportes
        supporters = room_data.get("supporters", [])
        if supporters:
            html += "<div style='margin-bottom: 5px;'><b style='color: #98c379;'>🪑 Superficies / Soportes:</b><ul style='margin: 3px 0 0 0; padding-left: 18px;'>"
            for s in supporters:
                items = s.get("items", [])
                items_text = (
                    f" &rarr; encima: <i>{', '.join(items)}</i>"
                    if items
                    else " &rarr; <i>(nada encima)</i>"
                )
                html += f"<li><b>{s['name']}</b>{items_text}</li>"
            html += "</ul></div>"

        # Objetos en el suelo
        items = room_data.get("items", [])
        if items:
            html += "<div style='margin-bottom: 5px;'><b style='color: #56b6c2;'>🔹 Objetos en el suelo:</b><ul style='margin: 3px 0 0 0; padding-left: 18px;'>"
            for it in items:
                cat = it.get("category", "object")
                icon = "🗝️" if cat == "key" else ("🥪" if cat == "food" else "🔹")
                html += f"<li>{icon} {it['name']}</li>"
            html += "</ul></div>"

        if not containers and not supporters and not items:
            html += "<div style='color: #5c6370; font-style: italic; margin-bottom: 5px;'>No hay objetos en esta sala.</div>"

        # Salidas / Conexiones
        exits = room_data.get("exits", [])
        if exits:
            html += "<div style='margin-top: 5px;'><b style='color: #d19a66;'>🚪 Salidas:</b><ul style='margin: 3px 0 0 0; padding-left: 18px;'>"
            dir_names_es = {"north": "Norte", "south": "Sur", "east": "Este", "west": "Oeste"}
            for ex in exits:
                d_es = dir_names_es.get(ex["direction"], ex["direction"].capitalize())
                if ex["is_door"]:
                    d_state = ex["door_state"]
                    state_lbl = (
                        "🟢 abierta"
                        if d_state == "open"
                        else ("🔴 bloqueada" if d_state == "locked" else "🟠 cerrada")
                    )
                    html += f"<li><b>{d_es}</b> &rarr; {ex['target_room']} [Puerta: <i>{ex['door_name']}</i>, {state_lbl}]</li>"
                else:
                    html += f"<li><b>{d_es}</b> &rarr; {ex['target_room']} (paso libre)</li>"
            html += "</ul></div>"

        html += "</div>"
        return html

    def _build_door_tooltip(self, conn: dict[str, Any]) -> str:
        door_name = conn.get("door_name", "Puerta")
        state = conn.get("door_state", "closed")
        r1 = conn.get("r1", "")
        r2 = conn.get("r2", "")
        matching_key = conn.get("matching_key")

        state_desc = (
            "<span style='color: #98c379; font-weight: bold;'>ABIERTA</span>"
            if state == "open"
            else (
                "<span style='color: #e06c75; font-weight: bold;'>BLOQUEADA CON LLAVE</span>"
                if state == "locked"
                else "<span style='color: #e5c07b; font-weight: bold;'>CERRADA</span>"
            )
        )

        html = "<div style='font-family: sans-serif; font-size: 12px; color: #abb2bf; padding: 4px; min-width: 200px;'>"
        html += f"<div style='font-size: 13px; font-weight: bold; color: #ffffff;'>🚪 {door_name.capitalize()} ({state_desc})</div>"
        html += "<hr style='border: 0; border-top: 1px solid #3e4451; margin: 4px 0;'/>"
        html += f"<div><b>Conecta:</b> {r1} &harr; {r2}</div>"
        if matching_key:
            html += f"<div style='margin-top: 3px; color: #e5c07b;'>🗝️ <b>Llave requerida:</b> {matching_key}</div>"
        html += "</div>"
        return html
