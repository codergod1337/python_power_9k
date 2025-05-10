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
    Canvas mit Zoom, Pan und kompletten Box-Editing:
    - Neue Boxen zeichnen
    - Hover- und Selektionszustände
    - Verschieben, Skalieren über Handles
    - Löschen per Entf-Taste
    """
    CORNER_SIZE = 6
    HANDLE_TOLERANCE = CORNER_SIZE * 2

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

        # Bild und View
        self.original_pixmap: QPixmap | None = None
        self.scale_factor = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0

        # Pan
        self.panning = False
        self.pan_start: QPoint | None = None
        self.pan_offset = (0.0, 0.0)

        # Zeichnen neuer Box
        self.start_pos: QPoint | None = None
        self.end_pos: QPoint | None = None

        # Edit State
        self.hovered_box_id: int | None = None
        self.selected_box_id: int | None = None
        self.hovered_corner: int | None = None
        self.resizing = False
        self.moving = False
        self.resize_corner: int | None = None
        self.edit_start: QPoint | None = None
        self.orig_rect: tuple[int,int,int,int] | None = None
        self.edit_idx: int | None = None

        # Label für neue Box
        self.current_label: str | None = None

    def set_pixmap(self, pixmap: QPixmap):
        self.original_pixmap = pixmap
        #self.scale_factor = 1.0
        #self.offset_x = self.offset_y = 0.0
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
        # Hintergrund zeichnen
        if self.original_pixmap:
            ow, oh = self.original_pixmap.width(), self.original_pixmap.height()
            sw, sh = ow*self.scale_factor, oh*self.scale_factor
            scaled = self.original_pixmap.scaled(int(sw), int(sh), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            w, h = self.width(), self.height()
            x0 = (w-scaled.width())//2 + int(self.offset_x)
            y0 = (h-scaled.height())//2 + int(self.offset_y)
            painter.drawPixmap(x0, y0, scaled)

            # Alle Boxen zeichnen
            proj = getattr(self.window(), 'project', None)
            if proj:
                for idx, (bid, label, x, y, bw, bh) in enumerate(proj.get_bboxes(proj.current_frame)):
                    p1 = self.image_to_widget(x, y)
                    p2 = self.image_to_widget(x+bw, y+bh)
                    if not (p1 and p2):
                        continue
                    rect = QRect(p1, p2).normalized()
                    # Pen bestimmen
                    if self.selected_box_id == bid and self.hovered_corner is not None:
                        pen = PRESELECTED_BOX_PEN
                    elif self.selected_box_id == bid:
                        pen = SELECTED_BOX_PEN
                    elif self.hovered_box_id == bid:
                        pen = PRESELECTED_BOX_PEN
                    else:
                        info = LABEL_CLASSES.get(label)
                        pen = QPen(info['color']) if info else QPen(Qt.red)
                        pen.setWidth(BOUNDING_BOX_PEN.width())
                    painter.setPen(pen)
                    painter.drawRect(rect)
                    # Handles für selected
                    if self.selected_box_id == bid:
                        brush = QBrush(pen.color())
                        for ci, corner in enumerate([rect.topLeft(), rect.topRight(), rect.bottomLeft(), rect.bottomRight()]):
                            # Handle nur farbig gefüllt
                            painter.fillRect(
                                corner.x()-self.CORNER_SIZE//2,
                                corner.y()-self.CORNER_SIZE//2,
                                self.CORNER_SIZE, self.CORNER_SIZE,
                                brush
                            )
                    # Label
                    text = f"{label}#{bid}"
                    fm = painter.fontMetrics()
                    painter.drawText(rect.bottomLeft()+QPoint(2, fm.height()+2), text)
        # Neue Box während Zeichnen
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
        img_x = (mx-x0_old)/self.scale_factor
        img_y = (my-y0_old)/self.scale_factor
        factor = 1.1 if event.angleDelta().y()>0 else 0.9
        self.scale_factor = max(min(self.scale_factor*factor,10),0.1)
        new_sw, new_sh = ow*self.scale_factor, oh*self.scale_factor
        base_x, base_y = (w-new_sw)/2, (h-new_sh)/2
        self.offset_x = mx - img_x*self.scale_factor - base_x
        self.offset_y = my - img_y*self.scale_factor - base_y
        self._clamp_offsets(new_sw,new_sh)
        self.update()
        self._update_status(int(mx),int(my))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            proj = getattr(self.window(), 'project', None)
            # Deselection: Klick außerhalb
            if self.selected_box_id is not None and proj:
                sel_rect = None
                for bid, label, x, y, bw, bh in proj.get_bboxes(proj.current_frame):
                    if bid == self.selected_box_id:
                        tl = self.image_to_widget(x, y)
                        br = self.image_to_widget(x + bw, y + bh)
                        if tl and br:
                            sel_rect = QRect(tl, br).normalized()
                        break
                if sel_rect and not sel_rect.contains(pos) and self.hovered_corner is None:
                    self.selected_box_id = None
                    self.update()
                    return
            # Resizing starten
            if self.selected_box_id is not None and self.hovered_corner is not None and proj:
                for idx, (bid, label, x, y, bw, bh) in enumerate(proj.get_bboxes(proj.current_frame)):
                    if bid == self.selected_box_id:
                        self.orig_rect = (x, y, bw, bh)
                        self.edit_idx = idx
                        break
                self.resizing = True
                self.resize_corner = self.hovered_corner
                self.edit_start = pos
                return
            # Box-Select
            if self.hovered_box_id is not None:
                self.selected_box_id = self.hovered_box_id
                self.resizing = self.moving = False
                self.hovered_corner = None
                self.start_pos = self.end_pos = None
                self.update()
                return
            # Move-Mode
            if self.selected_box_id is not None and proj:
                for idx, (bid, label, x, y, bw, bh) in enumerate(proj.get_bboxes(proj.current_frame)):
                    if bid != self.selected_box_id:
                        continue
                    rect_w = QRect(
                        self.image_to_widget(x, y),
                        self.image_to_widget(x + bw, y + bh)
                    ).normalized()
                    if rect_w.contains(pos):
                        self.moving = True
                        self.edit_start = pos
                        self.orig_rect = (x, y, bw, bh)
                        self.edit_idx = idx
                        return
            # Neues Zeichnen
            if self.selected_box_id is None:
                self.start_pos = pos
                self.end_pos = pos
        elif event.button() == Qt.RightButton and not (self.start_pos or self.resizing or self.moving):
            self.panning = True
            self.pan_start = event.pos()
            self.pan_offset = (self.offset_x, self.offset_y)

    def mouseMoveEvent(self, event):
        pos = event.pos()
        # update hovered_corner and hovered_box
        self.hovered_corner = None
        prev_box = self.hovered_box_id
        self.hovered_box_id = None
        proj = getattr(self.window(),'project',None)
        if proj:
            rects = proj.get_bboxes(proj.current_frame)
            # check corners for selected box
            if self.selected_box_id is not None:
                for idx, (bid,_,x,y,bw,bh) in enumerate(rects):
                    if bid!=self.selected_box_id: continue
                    rect_w = QRect(self.image_to_widget(x,y), self.image_to_widget(x+bw,y+bh)).normalized()
                    for ci,corner in enumerate([rect_w.topLeft(),rect_w.topRight(),rect_w.bottomLeft(),rect_w.bottomRight()]):
                        if (corner-pos).manhattanLength()<=self.HANDLE_TOLERANCE:
                            self.hovered_corner=ci
                            self.hovered_box_id=bid
                            break
                    if self.hovered_corner is not None:
                        break
            # check border hover for any box
            if self.hovered_box_id is None:
                for bid,_,x,y,bw,bh in proj.get_bboxes(proj.current_frame):
                    rect_w = QRect(self.image_to_widget(x,y), self.image_to_widget(x+bw,y+bh)).normalized()
                    px,py=pos.x(),pos.y()
                    if (((abs(px-rect_w.left())<=self.HANDLE_TOLERANCE or abs(px-rect_w.right())<=self.HANDLE_TOLERANCE)
                         and rect_w.top()<=py<=rect_w.bottom())
                        or
                        ((abs(py-rect_w.top())<=self.HANDLE_TOLERANCE or abs(py-rect_w.bottom())<=self.HANDLE_TOLERANCE)
                         and rect_w.left()<=px<=rect_w.right())):
                        self.hovered_box_id=bid
                        break
        if prev_box!=self.hovered_box_id:
            self.update()
        # Resizing
        if self.resizing and self.orig_rect and self.edit_idx is not None:
            dx=(pos.x()-self.edit_start.x())/self.scale_factor
            dy=(pos.y()-self.edit_start.y())/self.scale_factor
            x0,y0,w0,h0=self.orig_rect
            nx,ny,nw,nh=x0,y0,w0,h0
            ci=self.resize_corner
            if ci==0: nx,ny,nw,nh=x0+dx,y0+dy,w0-dx,h0-dy
            elif ci==1: ny,nw,nh=y0+dy,w0+dx,h0-dy
            elif ci==2: nx,nw,nh=x0+dx,w0-dx,h0+dy
            elif ci==3: nw,nh=w0+dx,h0+dy
            proj.bboxes[proj.current_frame][self.edit_idx]=(proj.bboxes[proj.current_frame][self.edit_idx][0],
                proj.bboxes[proj.current_frame][self.edit_idx][1],int(nx),int(ny),int(abs(nw)),int(abs(nh)))
            self.update();return
        # Moving
        if self.moving and self.orig_rect and self.edit_idx is not None:
            dx=(pos.x()-self.edit_start.x())/self.scale_factor
            dy=(pos.y()-self.edit_start.y())/self.scale_factor
            x0,y0,w0,h0=self.orig_rect
            proj.bboxes[proj.current_frame][self.edit_idx]=(proj.bboxes[proj.current_frame][self.edit_idx][0],
                proj.bboxes[proj.current_frame][self.edit_idx][1],int(x0+dx),int(y0+dy),w0,h0)
            self.update();return
        # Pan or draw
        if self.panning:
            delta=pos-self.pan_start
            self.offset_x,self.offset_y=self.pan_offset[0]+delta.x(),self.pan_offset[1]+delta.y()
            self._clamp_offsets(self.original_pixmap.width()*self.scale_factor,
                                 self.original_pixmap.height()*self.scale_factor)
            self.update()
        elif self.start_pos and self.selected_box_id is None:
            self.end_pos=pos;self.update()
        self._update_status(pos.x(),pos.y())

    def mouseReleaseEvent(self,event):
        if event.button()==Qt.LeftButton:
            if self.resizing: self.resizing=False;return
            if self.moving: self.moving=False;return
            if self.start_pos and self.end_pos and self.current_label and self.selected_box_id is None:
                i1=self.widget_to_image(self.start_pos.x(),self.start_pos.y())
                i2=self.widget_to_image(self.end_pos.x(),self.end_pos.y())
                if i1 and i2:
                    x1,y1=i1;x2,y2=i2;x,y=min(x1,x2),min(y1,y2)
                    w_box,h_box=abs(x2-x1),abs(y2-y1)
                    proj=self.window().project
                    proj.add_bbox(proj.current_frame,(self.current_label,x,y,w_box,h_box))
            self.start_pos=self.end_pos=None;self.update()
        elif event.button()==Qt.RightButton: self.panning=False

    def keyPressEvent(self,event):
        if event.key()==Qt.Key_Delete and self.selected_box_id is not None:
            proj=self.window().project;frame=proj.current_frame
            proj.bboxes[frame]=[b for b in proj.bboxes[frame] if b[0]!=self.selected_box_id]
            self.selected_box_id=None;self.update();return
        super().keyPressEvent(event)

    def image_to_widget(self,ix:int,iy:int)->QPoint|None:
        if not self.original_pixmap: return None
        ow,oh=self.original_pixmap.width(),self.original_pixmap.height()
        sw,sh=ow*self.scale_factor,oh*self.scale_factor
        x0=(self.width()-sw)/2+self.offset_x
        y0=(self.height()-sh)/2+self.offset_y
        return QPoint(int(x0+ix*self.scale_factor),int(y0+iy*self.scale_factor))

    def widget_to_image(self,wx:int,wy:int)->tuple[int,int]|None:
        if not self.original_pixmap: return None
        ow,oh=self.original_pixmap.width(),self.original_pixmap.height()
        sw,sh=ow*self.scale_factor,oh*self.scale_factor
        x0=(self.width()-sw)/2+self.offset_x
        y0=(self.height()-sh)/2+self.offset_y
        if wx<x0 or wx>x0+sw or wy<y0 or wy>y0+sh: return None
        return (int((wx-x0)/self.scale_factor),int((wy-y0)/self.scale_factor))

    def _clamp_offsets(self,sw:float,sh:float):
        w,h=self.width(),self.height()
        if sw>w: half=(sw-w)/2;self.offset_x=max(-half,min(self.offset_x,half))
        else: self.offset_x=0.0
        if sh>h: half=(sh-h)/2;self.offset_y=max(-half,min(self.offset_y,half))
        else: self.offset_y=0.0

    def _update_status(self,wx:int,wy:int):
        main=self.window()
        if hasattr(main,'update_status'):
            img=self.widget_to_image(wx,wy)
            ix,iy=img if img else (None,None)
            main.update_status(wx,wy,ix,iy,self.scale_factor)