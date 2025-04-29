import sys
from pathlib import Path
from PyQt5 import QtCore
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QAction, QFileDialog, QLabel, QVBoxLayout, QMessageBox,
    QHeaderView, QTableWidget, QTableWidgetItem, QStackedLayout
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
        self.current_label = next(iter(LABEL_CLASSES))

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
        # Frame-Status
        self.frame_label = QLabel("Frame: 0")
        self.statusBar().addPermanentWidget(self.frame_label)
        # Label-Klasse-Status
        self.label_status = QLabel("")
        self.statusBar().addPermanentWidget(self.label_status)

        # Canvas (Editor) verstecken
        self.canvas = Canvas()
        self.canvas.current_label = self.current_label
        self.canvas.hide()

        # Startscreen mit Tabelle
        self.start_screen = QWidget()
        start_layout = QVBoxLayout(self.start_screen)
        start_layout.addWidget(QLabel("Verfügbare Projekte:"))
        self.project_table = QTableWidget(0, 2)
        self.project_table.setHorizontalHeaderLabels(["Datei", "Zuletzt geändert"])
        hdr = self.project_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.project_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.project_table.setSelectionBehavior(QTableWidget.SelectRows)
        start_layout.addWidget(self.project_table)

        # Editor-Screen
        self.editor_screen = QWidget()
        editor_layout = QVBoxLayout(self.editor_screen)
        editor_layout.addWidget(self.canvas)

        # Stacked Layout
        central = QWidget()
        self.stack = QStackedLayout()
        central.setLayout(self.stack)
        self.stack.addWidget(self.start_screen)
        self.stack.addWidget(self.editor_screen)
        self.setCentralWidget(central)

        # Projekte-Ordner vorbereiten
        try:
            PROJECT_FOLDER.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Projektordner nicht anlegbar:\n{e}")

        # Aktionen
        new_action.triggered.connect(self.start_new_project)
        open_action.triggered.connect(self.open_existing_project)
        save_action.triggered.connect(self.save_project)
        self.project_table.cellDoubleClicked.connect(self.open_project_from_table)

        self.loader = VideoLoader()
        self.project = None
        self.load_project_list()

    def load_project_list(self):
        self.project_table.setRowCount(0)
        entries = []
        for fn in PROJECT_FOLDER.iterdir():
            if fn.is_file() and fn.name.endswith('_boxes.json'):
                entries.append((fn.stat().st_mtime, fn.name))
        entries.sort(key=lambda x: x[0], reverse=True)
        for mtime, name in entries:
            row = self.project_table.rowCount()
            self.project_table.insertRow(row)
            item_name = QTableWidgetItem(name)
            dt = QtCore.QDateTime.fromSecsSinceEpoch(int(mtime))
            item_date = QTableWidgetItem(dt.toString('yyyy-MM-dd HH:mm:ss'))
            self.project_table.setItem(row, 0, item_name)
            self.project_table.setItem(row, 1, item_date)

    def open_project_from_table(self, row, col):
        item = self.project_table.item(row, 0)
        if not item:
            return
        path = PROJECT_FOLDER / item.text()
        if path.exists():
            self.project = ProjectManager.load_project(path)
            self.loader.open(self.project.video_path)
            self.after_project_loaded()

    def start_new_project(self):
        if self.loader.select_video():
            self.project = ProjectManager(Path(self.loader.video_path))
            self.after_project_loaded(new=True)

    def open_existing_project(self):
        proj_path, _ = QFileDialog.getOpenFileName(
            self, "Projekt öffnen", str(PROJECT_FOLDER), "JSON Dateien (*.json)"
        )
        if proj_path:
            self.project = ProjectManager.load_project(Path(proj_path))
            self.loader.open(self.project.video_path)
            self.after_project_loaded()

    def after_project_loaded(self, new=False):
        name = Path(self.project.video_path).name
        self.setWindowTitle(f"Video Labeling Tool - {name}")
        self.save_action.setEnabled(True)
        self.on_label_selected(self.project.current_label or self.current_label)
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
        self.stack.setCurrentWidget(self.editor_screen)

    def on_label_selected(self, key):
        for k, act in self.label_actions.items():
            act.setChecked(k == key)
        self.current_label = key
        self.canvas.current_label = key
        disp = LABEL_CLASSES[key]['display_name']
        self.label_status.setText(f"Label: {disp}")

    def update_status(self, wx, wy, ix, iy, zf):
        if SHOW_STATUS_WINDOW_COORDS:
            self.win_coord_label.setText(f"W: {wx},{wy}")
        if SHOW_STATUS_IMAGE_COORDS:
            self.img_coord_label.setText(
                f"I: {ix if ix is not None else '-'}, {iy if iy is not None else '-'}"
            )
        if SHOW_STATUS_ZOOM:
            self.zoom_label.setText(f"Z: {zf:.2f}x")

    def save_project(self):
        self.project.current_frame = 0
        self.project.current_label = self.current_label
        self.project.scale_factor = self.canvas.scale_factor
        self.project.offset_x = self.canvas.offset_x
        self.project.offset_y = self.canvas.offset_y
        save_path = PROJECT_FOLDER / f"{Path(self.project.video_path).stem}_boxes.json"
        try:
            self.project.save_project(save_path)
            self.statusBar().showMessage(f"✅ Projekt gespeichert: {save_path}", 5000)
        except Exception as e:
            QMessageBox.critical(self, "Fehler", f"Speichern fehlgeschlagen:\n{e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())