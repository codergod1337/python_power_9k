# main.py 

import sys
from pathlib import Path
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QAction, QFileDialog, QLabel, QVBoxLayout, QMessageBox
)
from PyQt5.QtCore import Qt

from config import (
    PROJECT_FOLDER,
    MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT,
    SHOW_STATUS_WINDOW_COORDS, SHOW_STATUS_IMAGE_COORDS, SHOW_STATUS_ZOOM,
    STATUS_WINDOW_COORDS_PEN, STATUS_IMAGE_COORDS_PEN, STATUS_ZOOM_PEN,
    LABEL_CLASSES
)
from video_loader import VideoLoader
from project_manager import ProjectManager
from canvas import Canvas

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Labeling Tool")
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)

        # Datei-Menü
        file_menu = self.menuBar().addMenu("Datei")
        new_action = QAction("Neues Projekt", self)
        open_action = QAction("Projekt öffnen", self)
        save_action = QAction("Speichern", self)
        save_action.setEnabled(False)
        file_menu.addAction(new_action)
        file_menu.addAction(open_action)
        file_menu.addAction(save_action)
        self.save_action = save_action

        # Label-Klassen-Menü
        label_menu = self.menuBar().addMenu("Label-Klassen")
        self.label_actions = {}
        for key, info in LABEL_CLASSES.items():
            act = QAction(info["display_name"], self)
            act.setCheckable(True)
            act.triggered.connect(lambda checked, k=key: self.on_label_selected(k))
            label_menu.addAction(act)
            self.label_actions[key] = act
        default_key = next(iter(LABEL_CLASSES))
        self.current_label = default_key

        # Statusleiste
        if SHOW_STATUS_WINDOW_COORDS:
            self.win_coord_label = QLabel("W: 0,0")
            c = STATUS_WINDOW_COORDS_PEN.color()
            self.win_coord_label.setStyleSheet(
                f"color: rgb({c.red()},{c.green()},{c.blue()});"
            )
            self.statusBar().addPermanentWidget(self.win_coord_label)
        if SHOW_STATUS_IMAGE_COORDS:
            self.img_coord_label = QLabel("I: -,-")
            c = STATUS_IMAGE_COORDS_PEN.color()
            self.img_coord_label.setStyleSheet(
                f"color: rgb({c.red()},{c.green()},{c.blue()});"
            )
            self.statusBar().addPermanentWidget(self.img_coord_label)
        if SHOW_STATUS_ZOOM:
            self.zoom_label = QLabel("Z: 1.00x")
            c = STATUS_ZOOM_PEN.color()
            self.zoom_label.setStyleSheet(
                f"color: rgb({c.red()},{c.green()},{c.blue()});"
            )
            self.statusBar().addPermanentWidget(self.zoom_label)
        # Label-Status
        self.label_status = QLabel("")
        self.statusBar().addPermanentWidget(self.label_status)

        # Zentrales Widget und Layout
        central = QWidget()
        layout = QVBoxLayout(central)
        self.canvas = Canvas()
        self.canvas.current_label = self.current_label
        self.canvas.hide()
        layout.addWidget(self.canvas)
        self.setCentralWidget(central)

        # VideoLoader & ProjectManager
        self.loader = VideoLoader()
        self.project = None

        # Aktionen verbinden
        new_action.triggered.connect(self.start_new_project)
        open_action.triggered.connect(self.open_existing_project)
        save_action.triggered.connect(self.save_project)

    def _update_label_status(self):
        disp = LABEL_CLASSES.get(self.current_label, {}).get("display_name", "")
        self.label_status.setText(f"Label: {disp}")

    def on_label_selected(self, key):
        for k, act in self.label_actions.items():
            act.setChecked(k == key)
        self.current_label = key
        if hasattr(self.canvas, "current_label"):
            self.canvas.current_label = key
        self._update_label_status()

    def update_status(self, wx, wy, ix, iy, zf):
        if SHOW_STATUS_WINDOW_COORDS:
            self.win_coord_label.setText(f"W: {wx},{wy}")
        if SHOW_STATUS_IMAGE_COORDS:
            img_str = f"{ix},{iy}" if ix is not None else "-,-"
            self.img_coord_label.setText(f"I: {img_str}")
        if SHOW_STATUS_ZOOM:
            self.zoom_label.setText(f"Z: {zf:.2f}x")

    def start_new_project(self):
        if self.loader.select_video():
            self.project = ProjectManager(Path(self.loader.video_path))
            name = Path(self.loader.video_path).name
            self.setWindowTitle(f"Video Labeling Tool - {name}")
            self.save_action.setEnabled(True)
            # Standard-Label initial setzen
            self.on_label_selected(self.current_label)
            self.initialize_canvas(new=True)

    def open_existing_project(self):
        proj_path, _ = QFileDialog.getOpenFileName(
            self, "Projekt öffnen", str(PROJECT_FOLDER), "JSON Dateien (*.json)"
        )
        if proj_path:
            self.project = ProjectManager.load_project(Path(proj_path))
            self.loader.open(self.project.video_path)
            name = Path(self.project.video_path).name
            self.setWindowTitle(f"Video Labeling Tool - {name}")
            self.save_action.setEnabled(True)
            # Wiederhergestellte Label auswählen
            if self.project.current_label:
                self.on_label_selected(self.project.current_label)
            self.initialize_canvas(new=False)

    def initialize_canvas(self, new: bool):
        idx = self.project.current_frame
        pixmap = self.loader.get_frame(idx)
        if pixmap:
            self.canvas.set_pixmap(pixmap)
            self.canvas.show()
            if new:
                self.canvas.fit_to_window()
                self.project.scale_factor = self.canvas.scale_factor
                self.project.offset_x = self.canvas.offset_x
                self.project.offset_y = self.canvas.offset_y
            else:
                self.canvas.scale_factor = self.project.scale_factor
                self.canvas.offset_x = self.project.offset_x
                self.canvas.offset_y = self.project.offset_y
                self.canvas.update()
            self.update_status(0, 0, None, None, self.canvas.scale_factor)

    def save_project(self):
        """Speichert das Projekt ohne weiteren Dialog automatisch im Projekt-Ordner."""
        # 1) Session-Zustand aktualisieren
        self.project.current_frame   = 0  # sofern noch keine Frame-Navigation existiert
        self.project.current_label   = self.current_label
        self.project.scale_factor    = self.canvas.scale_factor
        self.project.offset_x        = self.canvas.offset_x
        self.project.offset_y        = self.canvas.offset_y

        # 2) Projekt-Ordner anlegen (falls noch nicht da)
        try:
            PROJECT_FOLDER.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Fehler",
                f"Projektordner konnte nicht erstellt werden:\n{e}"
            )
            return

        # 3) Pfad zusammenbauen und speichern
        save_path = PROJECT_FOLDER / f"{self.project.video_path.stem}_boxes.json"
        try:
            self.project.save_project(save_path)
            # Kurze Bestätigung in der Status-Leiste
            self.statusBar().showMessage(f"✅ Projekt gespeichert: {save_path}", 5000)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Fehler",
                f"Speichern fehlgeschlagen:\n{e}"
            )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())