from __future__ import annotations

import math
from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import QWidget


class RadarChartWidget(QWidget):
    """Widget de visualización con Gráfico de Telaraña (Radar / Spider Chart)
    renderizado de forma vectorial en alta resolución mediante QPainter.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RadarChartWidget")
        self.setMinimumSize(320, 300)

        # Estructura de ejes por defecto
        self._axes: list[dict[str, Any]] = []

    def set_data(self, axes: list[dict[str, Any]]) -> None:
        """Establece los datos de los ejes del gráfico.
        Cada dict debe contener:
        - 'label': str (nombre del eje)
        - 'score': float (valor normalizado entre 0.0 y 100.0)
        - 'display_text': str (texto formateado para mostrar en el vértice)
        """
        self._axes = list(axes)
        self.update()

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        width = self.width()
        height = self.height()

        cx = width / 2.0
        cy = height / 2.0

        # Margen perimetral para acomodar etiquetas de texto
        margin = 65.0
        max_radius = max(20.0, min(cx, cy) - margin)

        n_axes = len(self._axes)
        if n_axes < 3:
            # Mensaje en caso de no haber datos suficientes
            painter.setPen(QColor("#5c6370"))
            painter.setFont(QFont("Segoe UI", 11, QFont.Medium))
            painter.drawText(QRectF(0, 0, width, height), Qt.AlignCenter, "Sin datos de evaluación suficientes")
            return

        angle_step = (2.0 * math.pi) / n_axes
        start_angle = -math.pi / 2.0  # Empezar en el vértice superior vertical

        # 1. Dibujar telaraña de fondo (polígonos concéntricos para 20%, 40%, 60%, 80%, 100%)
        levels = [0.2, 0.4, 0.6, 0.8, 1.0]
        grid_pen = QPen(QColor("#353b47"), 1.0, Qt.SolidLine)
        outer_pen = QPen(QColor("#4c5565"), 1.5, Qt.SolidLine)

        for lvl in levels:
            lvl_radius = max_radius * lvl
            poly = QPolygonF()
            for i in range(n_axes):
                theta = start_angle + i * angle_step
                px = cx + lvl_radius * math.cos(theta)
                py = cy + lvl_radius * math.sin(theta)
                poly.append(QPointF(px, py))

            painter.setPen(outer_pen if lvl == 1.0 else grid_pen)
            painter.setBrush(QColor(33, 37, 43, 40) if lvl == 1.0 else Qt.NoBrush)
            painter.drawPolygon(poly)

        # 2. Dibujar líneas de eje radiales desde el centro hacia cada vértice
        axis_line_pen = QPen(QColor("#3e4451"), 1.0, Qt.DashLine)
        for i in range(n_axes):
            theta = start_angle + i * angle_step
            outer_x = cx + max_radius * math.cos(theta)
            outer_y = cy + max_radius * math.sin(theta)
            painter.setPen(axis_line_pen)
            painter.drawLine(QPointF(cx, cy), QPointF(outer_x, outer_y))

        # 3. Construir polígono de datos del agente
        data_polygon = QPolygonF()
        data_points: list[tuple[float, float, dict[str, Any]]] = []

        for i, ax in enumerate(self._axes):
            theta = start_angle + i * angle_step
            raw_score = float(ax.get("score", ax.get("value", 0.0)))
            clamped_score = max(0.0, min(100.0, raw_score)) / 100.0
            r = max_radius * clamped_score

            px = cx + r * math.cos(theta)
            py = cy + r * math.sin(theta)
            pt = QPointF(px, py)
            data_polygon.append(pt)
            data_points.append((px, py, ax))

        # Rellenar polígono con gradiente sutil
        gradient = QLinearGradient(cx, cy - max_radius, cx, cy + max_radius)
        gradient.setColorAt(0.0, QColor(89, 232, 255, 70))
        gradient.setColorAt(1.0, QColor(97, 175, 239, 35))

        painter.setPen(QPen(QColor("#59e8ff"), 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(QBrush(gradient))
        painter.drawPolygon(data_polygon)

        # 4. Dibujar nodos en cada vértice del polígono de datos
        for px, py, _ in data_points:
            # Halo exterior
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(89, 232, 255, 90))
            painter.drawEllipse(QPointF(px, py), 6.0, 6.0)

            # Punto central brillante
            painter.setBrush(QColor("#ffffff"))
            painter.setPen(QPen(QColor("#59e8ff"), 1.5))
            painter.drawEllipse(QPointF(px, py), 3.0, 3.0)

        # 5. Dibujar etiquetas de ejes alrededor del perímetro
        font_label = QFont("Segoe UI", 9, QFont.Bold)
        font_val = QFont("Segoe UI", 9, QFont.Normal)
        fm_label = QFontMetrics(font_label)
        fm_val = QFontMetrics(font_val)

        for i, ax in enumerate(self._axes):
            theta = start_angle + i * angle_step
            label_dist = max_radius + 18.0
            lx = cx + label_dist * math.cos(theta)
            ly = cy + label_dist * math.sin(theta)

            title_text = str(ax.get("label", ax.get("name", "")))
            disp_text = str(ax.get("display_text", ax.get("display", f"{ax.get('score', ax.get('value', 0)):.0f}%")))

            w_title = fm_label.horizontalAdvance(title_text)
            w_disp = fm_val.horizontalAdvance(disp_text)
            box_w = max(w_title, w_disp) + 10.0
            box_h = fm_label.height() + fm_val.height() + 4.0

            # Ajustar anclaje según la posición angular
            cos_t = math.cos(theta)
            sin_t = math.sin(theta)

            if abs(cos_t) < 0.2:
                # Arriba o abajo
                box_x = lx - box_w / 2.0
                box_y = (ly - box_h - 4.0) if sin_t < 0 else (ly + 4.0)
            elif cos_t > 0:
                # Lado derecho
                box_x = lx + 4.0
                box_y = ly - box_h / 2.0
            else:
                # Lado izquierdo
                box_x = lx - box_w - 4.0
                box_y = ly - box_h / 2.0

            # Dibujar etiqueta de título
            painter.setFont(font_label)
            painter.setPen(QColor("#dcdfe4"))
            painter.drawText(
                QRectF(box_x, box_y, box_w, fm_label.height()),
                Qt.AlignCenter,
                title_text,
            )

            # Dibujar valor formateado
            painter.setFont(font_val)
            score_val = float(ax.get("score", 0.0))
            if score_val >= 70.0:
                val_color = QColor("#98c379")
            elif score_val >= 40.0:
                val_color = QColor("#e5c07b")
            else:
                val_color = QColor("#e06c75")

            painter.setPen(val_color)
            painter.drawText(
                QRectF(box_x, box_y + fm_label.height() + 2.0, box_w, fm_val.height()),
                Qt.AlignCenter,
                disp_text,
            )
