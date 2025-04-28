# canvas.py

from PyQt5.QtWidgets import QWidget, QSizePolicy
from PyQt5.QtGui import QPainter, QPixmap, QPen
from PyQt5.QtCore import Qt, QRect, QPoint
from config import BOUNDING_BOX_PEN, LABEL_CLASSES

class Canvas(QWidget):
    """
    Zeichenfläche für Videoframes mit Zoom, Pan, Bounding-Box-Interaktion und Status-Updates.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)

        # Bild & View State
        self.original_pixmap: QPixmap | None = None
        self.scale_factor = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0

        # Pan State
        self.panning = False
        self.pan_start_mouse = None
        self.pan_start_offset = (0.0, 0.0)

        # Drawing State
        self.start_pos = None
        self.end_pos = None
        self.current_label: str | None = None

    def set_pixmap(self, pixmap: QPixmap):
        self.original_pixmap = pixmap
        self.scale_factor = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.update()

    def fit_to_window(self):
        if not self.original_pixmap:
            return
        ow, oh = self.original_pixmap.width(), self.original_pixmap.height()
        w, h = self.width(), self.height()
        self.scale_factor = min(w/ow, h/oh)
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        # Hintergrundbild
        if self.original_pixmap:
            ow, oh = self.original_pixmap.width(), self.original_pixmap.height()
            sw, sh = ow * self.scale_factor, oh * self.scale_factor
            scaled = self.original_pixmap.scaled(
                int(sw), int(sh), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            w, h = self.width(), self.height()
            x0 = (w - scaled.width()) / 2 + self.offset_x
            y0 = (h - scaled.height()) / 2 + self.offset_y
            painter.drawPixmap(int(x0), int(y0), scaled)

            # Gespeicherte Bounding-Boxen zeichnen
            proj = getattr(self.window(), 'project', None)
            if proj:
                for _id, label, x, y, w_box, h_box in proj.get_bboxes(proj.current_frame):
                    pt1 = self.image_to_widget(x, y)
                    pt2 = self.image_to_widget(x + w_box, y + h_box)
                    if pt1 and pt2:
                        info = LABEL_CLASSES.get(label)
                        if info:
                            pen = QPen(info['color'])
                        else:
                            pen = BOUNDING_BOX_PEN
                        pen.setWidth(BOUNDING_BOX_PEN.width())
                        painter.setPen(pen)

                        # Rechteck zeichnen
                        rect = QRect(pt1, pt2)
                        painter.drawRect(rect)

                        # ID und Label-Text unterhalb des Rechtecks zeichnen
                        text = f"{label}#{_id}"
                        fm = painter.fontMetrics()
                        # untere linke Ecke der Box
                        rect_bottom_left = QPoint(pt1.x(), pt2.y())
                        text_x = rect_bottom_left.x()
                        text_y = rect_bottom_left.y() + fm.height() + 2
                        painter.drawText(text_x, text_y, text)

        # Dynamische Bounding-Box beim Ziehen
        if self.start_pos and self.end_pos:
            painter.setPen(BOUNDING_BOX_PEN)
            painter.drawRect(QRect(self.start_pos, self.end_pos).normalized())

    def wheelEvent(self, event):
        if not self.original_pixmap:
            return
        ow, oh = self.original_pixmap.width(), self.original_pixmap.height()
        w, h = self.width(), self.height()
        old_sw, old_sh = ow * self.scale_factor, oh * self.scale_factor
        x0_old = (w - old_sw) / 2 + self.offset_x
        y0_old = (h - old_sh) / 2 + self.offset_y
        mx = event.position().x() if hasattr(event, 'position') else event.x()
        my = event.position().y() if hasattr(event, 'position') else event.y()
        img_x = (mx - x0_old) / self.scale_factor
        img_y = (my - y0_old) / self.scale_factor
        factor = 1.1 if event.angleDelta().y() > 0 else 0.9
        self.scale_factor = max(min(self.scale_factor * factor, 10.0), 0.1)
        new_sw, new_sh = ow * self.scale_factor, oh * self.scale_factor
        x0_new = mx - img_x * self.scale_factor
        y0_new = my - img_y * self.scale_factor
        base_x, base_y = (w - new_sw) / 2, (h - new_sh) / 2
        self.offset_x = x0_new - base_x
        self.offset_y = y0_new - base_y
        self._clamp_offsets(new_sw, new_sh)
        self.update()
        self._update_status(int(mx), int(my))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_pos = event.pos()
            self.end_pos = self.start_pos
        elif event.button() == Qt.RightButton and not self.start_pos:
            self.panning = True
            self.pan_start_mouse = event.pos()
            self.pan_start_offset = (self.offset_x, self.offset_y)

    def mouseMoveEvent(self, event):
        if self.panning:
            self._handle_pan(event)
        else:
            wx, wy = event.x(), event.y()
            if self.start_pos:
                self.end_pos = event.pos()
                self.update()
            self._update_status(wx, wy)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.start_pos:
            self.end_pos = event.pos()
            # Speichern der neuen Bounding-Box
            img1 = self.widget_to_image(self.start_pos.x(), self.start_pos.y())
            img2 = self.widget_to_image(self.end_pos.x(), self.end_pos.y())
            if img1 and img2 and self.current_label:
                x1, y1 = img1
                x2, y2 = img2
                x, y = min(x1, x2), min(y1, y2)
                w_box, h_box = abs(x2 - x1), abs(y2 - y1)
                proj = self.window().project
                proj.add_bbox(proj.current_frame, (self.current_label, x, y, w_box, h_box))
            # Cleanup
            self.start_pos = None
            self.end_pos = None
            self.update()
        elif event.button() == Qt.RightButton and self.panning:
            self.panning = False
            self.pan_start_mouse = None
            self.pan_start_offset = (0.0, 0.0)

    def _handle_pan(self, event):
        if not self.pan_start_mouse:
            return
        delta = event.pos() - self.pan_start_mouse
        self.offset_x = self.pan_start_offset[0] + delta.x()
        self.offset_y = self.pan_start_offset[1] + delta.y()
        if self.original_pixmap:
            ow, oh = self.original_pixmap.width(), self.original_pixmap.height()
            self._clamp_offsets(ow * self.scale_factor, oh * self.scale_factor)
        self.update()
        self._update_status(event.x(), event.y())

    def widget_to_image(self, wx: int, wy: int) -> tuple[int, int] | None:
        if not self.original_pixmap:
            return None
        ow, oh = self.original_pixmap.width(), self.original_pixmap.height()
        sw, sh = ow * self.scale_factor, oh * self.scale_factor
        x0 = (self.width() - sw) / 2 + self.offset_x
        y0 = (self.height() - sh) / 2 + self.offset_y
        if wx < x0 or wx > x0 + sw or wy < y0 or wy > y0 + sh:
            return None
        ix = (wx - x0) / self.scale_factor
        iy = (wy - y0) / self.scale_factor
        return (int(ix), int(iy))

    def image_to_widget(self, ix: int, iy: int) -> QPoint | None:
        if not self.original_pixmap:
            return None
        ow, oh = self.original_pixmap.width(), self.original_pixmap.height()
        sw, sh = ow * self.scale_factor, oh * self.scale_factor
        x0 = (self.width() - sw) / 2 + self.offset_x
        y0 = (self.height() - sh) / 2 + self.offset_y
        wx = x0 + ix * self.scale_factor
        wy = y0 + iy * self.scale_factor
        return QPoint(int(wx), int(wy))

    def _clamp_offsets(self, sw: float, sh: float):
        w, h = self.width(), self.height()
        if sw > w:
            half = (sw - w) / 2
            self.offset_x = max(-half, min(self.offset_x, half))
        else:
            self.offset_x = 0.0
        if sh > h:
            half = (sh - h) / 2
            self.offset_y = max(-half, min(self.offset_y, half))
        else:
            self.offset_y = 0.0

    def _update_status(self, wx: int, wy: int):
        main = self.window()
        if hasattr(main, 'update_status'):
            img = self.widget_to_image(wx, wy)
            ix, iy = img if img else (None, None)
            main.update_status(wx, wy, ix, iy, self.scale_factor)