# config.py
from pathlib import Path
from PyQt5.QtGui import QPen, QColor
from PyQt5.QtCore import Qt

# Ordner für Eingabe-Videos und Projektdateien
INPUT_FOLDER: Path = Path("data") / "input"
PROJECT_FOLDER: Path = Path("data") / "projects"

# Unterstützte Video-Formate
SUPPORTED_FORMATS = [".mp4", ".avi", ".mov", ".mkv", ".flv", ".webm"]

# Minimale Fenstergröße
MIN_WINDOW_WIDTH: int = 800
MIN_WINDOW_HEIGHT: int = 600

# Status-Bar Toggles und Pens
SHOW_STATUS_WINDOW_COORDS: bool = True
STATUS_WINDOW_COORDS_PEN = QPen(QColor(0, 0, 0))  # Schwarz
STATUS_WINDOW_COORDS_PEN.setWidth(1)
STATUS_WINDOW_COORDS_PEN.setStyle(Qt.SolidLine)

SHOW_STATUS_IMAGE_COORDS: bool = True
STATUS_IMAGE_COORDS_PEN = QPen(QColor(0, 0, 255))  # Blau
STATUS_IMAGE_COORDS_PEN.setWidth(1)
STATUS_IMAGE_COORDS_PEN.setStyle(Qt.SolidLine)

SHOW_STATUS_ZOOM: bool = True
STATUS_ZOOM_PEN = QPen(QColor(255, 0, 255))  # Magenta
STATUS_ZOOM_PEN.setWidth(1)
STATUS_ZOOM_PEN.setStyle(Qt.SolidLine)

# Bounding-Box Pen
BOUNDING_BOX_PEN = QPen(QColor(255, 0, 0))  # Rot
BOUNDING_BOX_PEN.setWidth(2)
BOUNDING_BOX_PEN.setStyle(Qt.SolidLine)

# === Pen zum Aufziehen neuer Bounding-Boxes ===
DRAWING_BOX_PEN = QPen(QColor(200, 200, 200))  # Grau
DRAWING_BOX_PEN.setWidth(1)
DRAWING_BOX_PEN.setStyle(Qt.DashLine)

# Hover-Zustand (Pre-Select)
PRESELECTED_BOX_PEN = QPen(QColor(255, 165, 0))  # Orange
PRESELECTED_BOX_PEN.setWidth(2)
PRESELECTED_BOX_PEN.setStyle(Qt.DashLine)

# Aktivierte Box (Select)
SELECTED_BOX_PEN = QPen(QColor(0, 255, 0))  # Grün
SELECTED_BOX_PEN.setWidth(2)
SELECTED_BOX_PEN.setStyle(Qt.SolidLine)

# === Label-Klassen-Konfiguration ===
# Hier definierst du deine Klassen und kannst pro Klasse beliebig viele Features anlegen.
# Format: "klasse_schluessel": {
#    "display_name": <Anzeigename>,
#    "color": QColor(...),
#    "features": { <beliebige Schlüssel-Werte-Paare> }
# }
LABEL_CLASSES: dict[str, dict] = {
    "person": {
        "display_name": "Person",
        "color": QColor(0, 200, 0),  # Grün
        "features": {
            # z.B.: "occluded": False
        }
    },
    "car": {
        "display_name": "Car",
        "color": QColor(0, 0, 255),  # Blau
        "features": {
            # z.B.: "license_plate": None
        }
    },
    "truck": {
        "display_name": "Truck",
        "color": QColor(200, 0, 0),  # Rot
        "features": {}
    },
    # Weitere Klassen hier hinzufügen...
}
