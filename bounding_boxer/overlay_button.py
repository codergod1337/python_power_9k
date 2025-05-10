from PyQt5.QtWidgets import QLabel
from PyQt5.QtGui import QPainter, QBrush, QPen, QColor, QFont
from PyQt5.QtCore import Qt, QRect, pyqtSignal


class OverlayButton(QLabel):
    clicked = pyqtSignal()

    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.setText(text)
        self.setFixedSize(48, 48)
        self.setCursor(Qt.PointingHandCursor)
        self.hovered = False
        self.font = QFont("Arial", 20, QFont.Bold)
        self.bg_color = QColor(255, 255, 255, 100)
        self.hover_color = QColor(255, 255, 255, 160)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Hintergrund
        color = self.hover_color if self.hovered else self.bg_color
        painter.setBrush(QBrush(color))
        painter.setPen(QPen(QColor(100, 100, 100, 180)))
        painter.drawRoundedRect(QRect(0, 0, self.width(), self.height()), 10, 10)

        # Text
        painter.setFont(self.font)
        painter.setPen(Qt.black)
        painter.drawText(self.rect(), Qt.AlignCenter, self.text())

    def enterEvent(self, event):
        self.hovered = True
        self.update()

    def leaveEvent(self, event):
        self.hovered = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()