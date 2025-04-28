# project_manager.py

import json
from pathlib import Path

class ProjectManager:
    """Verwaltert Session-Daten für Video-Labeling-Projekte, einschließlich Session-Zustand, aktuellen Labels und Labelzählern."""
    def __init__(self, video_path: Path, project_path: Path | None = None):
        self.video_path = video_path
        self.project_path = project_path
        # frame_index -> list of tuples (id:int, label:str, x:int, y:int, w:int, h:int)
        self.bboxes: dict[int, list[tuple[int, str, int, int, int, int]]] = {}
        # Label-Counter pro Klasse
        self.label_counters: dict[str, int] = {}
        # Session-Zustand
        self.current_frame: int = 0
        self.current_label: str | None = None
        self.scale_factor: float = 1.0
        self.offset_x: float = 0.0
        self.offset_y: float = 0.0

    def get_next_id(self, label: str) -> int:
        """Gibt nächste ID für eine Label-Klasse zurück und inkrementiert den Zähler."""
        if label not in self.label_counters:
            self.label_counters[label] = 1
        else:
            self.label_counters[label] += 1
        return self.label_counters[label]

    @classmethod
    def load_project(cls, project_path: Path) -> 'ProjectManager':
        """Lädt bestehendes Projekt aus JSON und stellt Session und Labelzähler wieder her."""
        data = json.loads(project_path.read_text())
        pm = cls(Path(data.get("video", "")), project_path)
        # Labelzähler wiederherstellen
        pm.label_counters = data.get("counters", {})
        # Bounding-Boxen laden
        raw = data.get("bboxes", {})
        for frame_str, items in raw.items():
            frame = int(frame_str)
            pm.bboxes[frame] = []
            for item in items:
                _id = item.get("id")
                label = item.get("label")
                x, y, w, h = item.get("rect", [0, 0, 0, 0])
                pm.bboxes[frame].append((_id, label, x, y, w, h))
        # Session-Zustand
        pm.current_frame = data.get("current_frame", 0)
        pm.current_label = data.get("current_label", None)
        view = data.get("view", {})
        pm.scale_factor = view.get("scale_factor", 1.0)
        pm.offset_x = view.get("offset_x", 0.0)
        pm.offset_y = view.get("offset_y", 0.0)
        return pm

    def add_bbox(self, frame_idx: int, label_rect: tuple[str, int, int, int, int]) -> None:
        """Fügt eine Bounding-Box mit Label und globaler ID hinzu."""
        label, x, y, w, h = label_rect
        _id = self.get_next_id(label)
        self.bboxes.setdefault(frame_idx, []).append((_id, label, x, y, w, h))

    def get_bboxes(self, frame_idx: int) -> list[tuple[int, str, int, int, int, int]]:
        """Gibt Liste von Boxen (id, label, x, y, w, h) für einen Frame zurück."""
        return self.bboxes.get(frame_idx, [])

    def save_project(self, project_path: Path | None = None) -> None:
        """Speichert Projekt als JSON inklusive Session, Labelzähler und Bounding-Boxen."""
        if project_path:
            self.project_path = project_path
        if not self.project_path:
            raise ValueError("Kein Projektpfad gesetzt.")
        bboxes_out = {}
        for frame, shapes in self.bboxes.items():
            items = []
            for _id, label, x, y, w, h in shapes:
                items.append({"id": _id, "label": label, "rect": [x, y, w, h]})
            bboxes_out[str(frame)] = items
        data = {
            "video": str(self.video_path),
            "bboxes": bboxes_out,
            "current_frame": self.current_frame,
            "current_label": self.current_label,
            "counters": self.label_counters,
            "view": {
                "scale_factor": self.scale_factor,
                "offset_x": self.offset_x,
                "offset_y": self.offset_y
            }
        }
        self.project_path.parent.mkdir(parents=True, exist_ok=True)
        self.project_path.write_text(json.dumps(data, indent=2))