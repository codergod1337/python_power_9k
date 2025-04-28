# video_loader.py
import cv2
from pathlib import Path
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtGui import QImage, QPixmap

from config import INPUT_FOLDER, SUPPORTED_FORMATS

class VideoLoader:
    """
    Lädt ein Video aus INPUT_FOLDER und liefert Frames als QPixmap.
    """
    def __init__(self):
        self.cap = None
        self.video_path: Path | None = None

    def select_video(self) -> bool:
        """Öffnet einen Datei-Dialog und lädt das ausgewählte Video."""
        file_filter = "Videos ({})".format(
            " ".join(f"*{ext}" for ext in SUPPORTED_FORMATS)
        )
        path, _ = QFileDialog.getOpenFileName(
            None,
            "Video-Datei auswählen",
            str(INPUT_FOLDER),
            file_filter
        )
        if not path:
            return False
        return self.open(Path(path))

    def open(self, path: Path) -> bool:
        """Öffnet das Video mit OpenCV."""
        self.cap = cv2.VideoCapture(str(path))
        if not self.cap.isOpened():
            print(f"Fehler: Kann Video nicht öffnen: {path}")
            return False
        self.video_path = path
        return True

    def frame_count(self) -> int:
        """Gibt die Gesamtanzahl der Frames zurück."""
        if not self.cap:
            return 0
        return int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

    def get_frame(self, index: int) -> QPixmap | None:
        """Lädt den Frame mit dem gegebenen Index als QPixmap."""
        if not self.cap:
            return None
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, index)
        success, frame = self.cap.read()
        if not success:
            print(f"Fehler: Frame {index} konnte nicht geladen werden.")
            return None
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        qimg = QImage(
            frame_rgb.data,
            w,
            h,
            bytes_per_line,
            QImage.Format_RGB888
        )
        return QPixmap.fromImage(qimg)