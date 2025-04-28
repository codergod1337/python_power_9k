# canvas.py
from PyQt5.QtWidgets import QWidget, QSizePolicy
from PyQt5.QtGui import QPainter, QPixmap, QPen, QColor, QBrush
from PyQt5.QtCore import Qt, QRect, QPoint
from config import (
    BOUNDING_BOX_PEN,
    DRAWING_BOX_PEN,
    PRESELECTED_BOX_PEN,
    SELECTED_BOX_PEN,
    LABEL_CLASSES
)

class Canvas(QWidget):
    """
    Zeichenfläche für Videoframes mit Zoom, Pan, Box-Editing und Status-Updates.
    Ermöglicht Aufziehen, Selektion, Verschieben, Skalieren und Löschen von Bounding-Boxen.
    """
    HOVER_TOLERANCE = 5   # Pixel-Toleranz zum Erkennen der Boxkanten
    CORNER_SIZE = 6       # Größe der Resizing-Handles (Quadrate)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

        # Bild- und Ansichts-Status
        self.original_pixmap: QPixmap | None = None
        self.scale_factor = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0

        # Pan-Zustand
        self.panning = False
        self.pan_start: QPoint | None = None
        self.pan_offset = (0.0, 0.0)

        # Neuer Box-Zeichnen
        self.start_pos: QPoint | None = None
        self.end_pos: QPoint | None = None

        # Edit-Zustand
        self.hovered_box_id: int | None = None
        self.selected_box_id: int | None = None
        self.resizing = False
        self.moving = False
        self.resize_corner: int | None = None  # 0-3 for corners
        self.edit_start: QPoint | None = None
        self.orig_rect: tuple[int,int,int,int] | None = None  # x,y,w,h in image coords
        self.edit_idx: int | None = None

        # Aktuelles Label für neue Box
        self.current_label: str | None = None

    def set_pixmap(self, pixmap: QPixmap):
        self.original_pixmap = pixmap
        self.scale_factor = 1.0
        self.offset_x = self.offset_y = 0.0
        self.update()

    def fit_to_window(self):
        if not self.original_pixmap:
            return
        ow, oh = self.original_pixmap.width(), self.original_pixmap.height()
        w, h = self.width(), self.height()
        self.scale_factor = min(w/ow, h/oh)
        self.offset_x = self.offset_y = 0.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        # Hintergrundbild
        if self.original_pixmap:
            ow, oh = self.original_pixmap.width(), self.original_pixmap.height()
            sw, sh = ow*self.scale_factor, oh*self.scale_factor
            scaled = self.original_pixmap.scaled(int(sw), int(sh), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            w, h = self.width(), self.height()
            x0 = (w - scaled.width())//2 + int(self.offset_x)
            y0 = (h - scaled.height())//2 + int(self.offset_y)
            painter.drawPixmap(x0, y0, scaled)

            # gespeicherte Boxen
            proj = getattr(self.window(), 'project', None)
            if proj:
                for idx, (bid, label, x, y, bw, bh) in enumerate(proj.get_bboxes(proj.current_frame)):
                    p1 = self.image_to_widget(x, y)
                    p2 = self.image_to_widget(x+bw, y+bh)
                    if not (p1 and p2):
                        continue
                    rect = QRect(p1, p2).normalized()
                    # Pen wählen
                    if self.selected_box_id == bid:
                        pen = SELECTED_BOX_PEN
                    elif self.hovered_box_id == bid:
                        pen = PRESELECTED_BOX_PEN
                    else:
                        info = LABEL_CLASSES.get(label)
                        pen = QPen(info['color']) if info else QPen(Qt.red)
                        pen.setWidth(BOUNDING_BOX_PEN.width())
                    painter.setPen(pen)
                    painter.drawRect(rect)
                    # Handles
                    if self.selected_box_id == bid:
                        brush = QBrush(pen.color())
                        for corner in [rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight()]:
                            painter.fillRect(
                                corner.x()-self.CORNER_SIZE//2,
                                corner.y()-self.CORNER_SIZE//2,
                                self.CORNER_SIZE,
                                self.CORNER_SIZE,
                                brush
                            )
                    # Label unterhalb
                    text = f"{label}#{bid}"
                    fm = painter.fontMetrics()
                    painter.drawText(rect.bottomLeft()+QPoint(2, fm.height()+2), text)

        # Ziehen neuer Box
        if self.start_pos and self.end_pos and not (self.resizing or self.moving):
            painter.setPen(DRAWING_BOX_PEN)
            painter.drawRect(QRect(self.start_pos, self.end_pos).normalized())

    def wheelEvent(self, event):
        if not self.original_pixmap:
            return
        ow, oh = self.original_pixmap.width(), self.original_pixmap.height()
        w, h = self.width(), self.height()
        mx = event.position().x() if hasattr(event, 'position') else event.x()
        my = event.position().y() if hasattr(event, 'position') else event.y()
        old_sw, old_sh = ow*self.scale_factor, oh*self.scale_factor
        x0_old = (w-old_sw)/2 + self.offset_x
        y0_old = (h-old_sh)/2 + self.offset_y
        img_x = (mx - x0_old)/self.scale_factor
        img_y = (my - y0_old)/self.scale_factor
        factor = 1.1 if event.angleDelta().y()>0 else 0.9
        self.scale_factor = max(min(self.scale_factor*factor, 10.0), 0.1)
        new_sw, new_sh = ow*self.scale_factor, oh*self.scale_factor
        base_x, base_y = (w-new_sw)/2, (h-new_sh)/2
        self.offset_x = mx - img_x*self.scale_factor - base_x
        self.offset_y = my - img_y*self.scale_factor - base_y
        self._clamp_offsets(new_sw, new_sh)
        self.update()
        self._update_status(int(mx), int(my))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Hover-Select
            if self.hovered_box_id is not None:
                self.selected_box_id = self.hovered_box_id
                # Reset states
                self.resizing = self.moving = False
                self.edit_idx = None
                self.start_pos = self.end_pos = None
                self.update()
                return
            # Edit-Mode
            if self.selected_box_id is not None:
                proj = self.window().project
                boxes = proj.get_bboxes(proj.current_frame)
                for idx, (bid, label, x, y, bw, bh) in enumerate(boxes):
                    if bid != self.selected_box_id:
                        continue
                    rect_w = QRect(
                        self.image_to_widget(x, y),
                        self.image_to_widget(x+bw, y+bh)
                    ).normalized()
                    pos = event.pos()
                    # Resize corners
                    corners = [rect_w.topLeft(), rect_w.topRight(), rect_w.bottomLeft(), rect_w.bottomRight()]
                    for ci, pt in enumerate(corners):
                        if (pt - pos).manhattanLength() <= self.HOVER_TOLERANCE:
                            self.resizing = True
                            self.resize_corner = ci
                            self.edit_start = pos
                            self.orig_rect = (x, y, bw, bh)
                            self.edit_idx = idx
                            return
                    # Move inside
                    if rect_w.contains(pos):
                        self.moving = True
                        self.edit_start = pos
                        self.orig_rect = (x, y, bw, bh)
                        self.edit_idx = idx
                        return
            # New Box
            self.start_pos = event.pos()
            self.end_pos = self.start_pos
        elif event.button() == Qt.RightButton and not (self.start_pos or self.resizing or self.moving):
            self.panning = True
            self.pan_start = event.pos()
            self.pan_offset = (self.offset_x, self.offset_y)

    def mouseMoveEvent(self, event):
        pos = event.pos()
        # Hover detection on borders
        prev = self.hovered_box_id
        self.hovered_box_id = None
        proj = getattr(self.window(), 'project', None)
        if proj:
            tol = self.HOVER_TOLERANCE
            for bid, label, x, y, bw, bh in proj.get_bboxes(proj.current_frame):
                rect_w = QRect(
                    self.image_to_widget(x, y),
                    self.image_to_widget(x+bw, y+bh)
                ).normalized()
                px, py = pos.x(), pos.y()
                on_border = (((abs(px-rect_w.left())<=tol or abs(px-rect_w.right())<=tol)
                              and rect_w.top()<=py<=rect_w.bottom())
                             or
                             ((abs(py-rect_w.top())<=tol or abs(py-rect_w.bottom())<=tol)
                              and rect_w.left()<=px<=rect_w.right()))
                if on_border:
                    self.hovered_box_id = bid
                    break
        if prev != self.hovered_box_id:
            self.update()

        # Resizing
        if self.resizing and self.orig_rect and self.edit_idx is not None:
            dx = (pos.x()-self.edit_start.x())/self.scale_factor
            dy = (pos.y()-self.edit_start.y())/self.scale_factor
            x0,y0,w0,h0 = self.orig_rect
            nx,ny,nw,nh = x0,y0,w0,h0
            ci = self.resize_corner
            if ci == 0:
                nx, ny, nw, nh = x0+dx, y0+dy, w0-dx, h0-dy
            elif ci == 1:
                ny, nw, nh = y0+dy, w0+dx, h0-dy
            elif ci == 2:
                nx, nw, nh = x0+dx, w0-dx, h0+dy
            elif ci == 3:
                nw, nh = w0+dx, h0+dy
            proj.bboxes[proj.current_frame][self.edit_idx] = (
                proj.bboxes[proj.current_frame][self.edit_idx][0],
                proj.bboxes[proj.current_frame][self.edit_idx][1],
                int(nx), int(ny), int(abs(nw)), int(abs(nh))
            )
            self.update()
            return

        # Moving
        if self.moving and self.orig_rect and self.edit_idx is not None:
            dx = (pos.x()-self.edit_start.x())/self.scale_factor
            dy = (pos.y()-self.edit_start.y())/self.scale_factor
            x0,y0,w0,h0 = self.orig_rect
            proj.bboxes[proj.current_frame][self.edit_idx] = (
                proj.bboxes[proj.current_frame][self.edit_idx][0],
                proj.bboxes[proj.current_frame][self.edit_idx][1],
                int(x0+dx), int(y0+dy), w0, h0
            )
            self.update()
            return

        # Pan
        if self.panning:
            delta = pos - self.pan_start
            self.offset_x = self.pan_offset[0] + delta.x()
            self.offset_y = self.pan_offset[1] + delta.y()
            self._clamp_offsets(
                self.original_pixmap.width()*self.scale_factor,
                self.original_pixmap.height()*self.scale_factor
            )
            self.update()
        # Drawing
        elif self.start_pos:
            self.end_pos = pos
            self.update()
        self._update_status(pos.x(), pos.y())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.resizing:
                self.resizing = False
                self.resize_corner = None
                return
            if self.moving:
                self.moving = False
                return
            if self.start_pos and self.end_pos and self.current_label:
                i1 = self.widget_to_image(self.start_pos.x(), self.start_pos.y())
                i2 = self.widget_to_image(self.end_pos.x(), self.end_pos.y())
                if i1 and i2:
                    x1,y1 = i1; x2,y2 = i2
                    x,y = min(x1,x2), min(y1,y2)
                    w_box, h_box = abs(x2-x1), abs(y2-y1)
                    proj = self.window().project
                    bid = proj.get_next_id(self.current_label)
                    proj.add_bbox(proj.current_frame, (self.current_label, x, y, w_box, h_box))
            self.start_pos = self.end_pos = None
            self.update()
        elif event.button() == Qt.RightButton:
            self.panning = False

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete and self.selected_box_id is not None:
            proj = self.window().project
            frame = proj.current_frame
            proj.bboxes[frame] = [b for b in proj.bboxes[frame] if b[0] != self.selected_box_id]
            self.selected_box_id = None
            self.update()
        else:
            super().keyPressEvent(event)

    def image_to_widget(self, ix: int, iy: int) -> QPoint | None:
        if not self.original_pixmap:
            return None
        ow, oh = self.original_pixmap.width(), self.original_pixmap.height()
        sw, sh = ow*self.scale_factor, oh*self.scale_factor
        x0 = (self.width()-sw)/2 + self.offset_x
        y0 = (self.height()-sh)/2 + self.offset_y
        wx = x0 + ix*self.scale_factor
        wy = y0 + iy*self.scale_factor
        return QPoint(int(wx), int(wy))

    def widget_to_image(self, wx: int, wy: int) -> tuple[int, int] | None:
        if not self.original_pixmap:
            return None
        ow, oh = self.original_pixmap.width(), self.original_pixmap.height()
        sw, sh = ow*self.scale_factor, oh*self.scale_factor
        x0 = (self.width()-sw)/2 + self.offset_x
        y0 = (self.height()-sh)/2 + self.offset_y
        if wx < x0 or wx > x0+sw or wy < y0 or wy > y0+sh:
            return None
        ix = (wx - x0)/self.scale_factor
        iy = (wy - y0)/self.scale_factor
        return (int(ix), int(iy))

    def _clamp_offsets(self, sw: float, sh: float):
        w, h = self.width(), self.height()
        if sw > w:
            half = (sw-w)/2
            self.offset_x = max(-half, min(self.offset_x, half))
        else:
            self.offset_x = 0.0
        if sh > h:
            half = (sh-h)/2
            self.offset_y = max(-half, min(self.offset_y, half))
        else:
            self.offset_y = 0.0

    def _update_status(self, wx: int, wy: int):
        main = self.window()
        if hasattr(main, 'update_status'):
            img = self.widget_to_image(wx, wy)
            ix, iy = img if img else (None, None)
            main.update_status(wx, wy, ix, iy, self.scale_factor)