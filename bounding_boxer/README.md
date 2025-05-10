# Video Labeling Tool

**Ein interaktives Python-/PyQt5-basiertes Labeling-Tool** zum Annotieren von Videos mit rechteckigen Bounding-Boxen. Es unterstützt:

- Laden von Videos & Abspeichern von Sessions in JSON
- Zoomen, Panning und Frame-Navigation
- Zeichnen, Selektieren, Verschieben, Skalieren und Löschen von Bounding-Boxen
- Konfigurierbare Label-Klassen mit individuellen Farben
- Projekt-Management über Start-Screen mit Projektliste
- Persistente Status-Wiederherstellung (Zoom, Offsets, aktueller Frame, gewähltes Label)

---

## 🚀 Voraussetzungen

- Python 3.8+ all312
- PyQt5
- OpenCV (für Video-Laden)

```bash
pip install PyQt5 opencv-python
```

---

## 📁 Projektstruktur

```text
.
├── main.py              # Hauptfenster, Menü & Startscreen
├── config.py            # Konfiguration (Ordner, Stile, Label-Klassen)
├── video_loader.py      # Video-Auswahl & Frame-Extraktion
├── project_manager.py   # Projekt-Session (Frames & BBoxes) laden/speichern
├── canvas.py            # Zeichenfläche mit Zoom, Pan & Box-Editing
└── README.md            # Dieses Dokument
```

---

## ⚙️ Konfiguration (`config.py`)

- **PROJECT_FOLDER**: Default-Ordner für Session-Dateien (`*_boxes.json`).
- **MIN_WINDOW_WIDTH / HEIGHT**: Minimale Fenstergröße.
- **SHOW_STATUS_***: Booleans zum Ein-/Ausblenden der Status-Bar-Elemente (Fenster-Coords, Bild-Coords, Zoom, Frame).
- **PENS**: `STATUS_*_PEN` legt Farbe (RGB) und Stärke der Statustexte fest.
- **LABEL_CLASSES**: Dict `key → {display_name, color, ...}` der verfügbaren Label-Typen.

---

## 🖱️ Verwendung

1. **Starten:**
   ```bash
   python main.py
   ```
2. **Neues Projekt:**
   - Klick auf **Datei → Neues Projekt** oder im Startscreen auf Zelle doppelklicken
   - Wähle deine Videodatei im Input-Ordner aus
3. **Projekt öffnen:**
   - Wähle JSON im Startscreen oder über **Datei → Projekt öffnen**
4. **Annotieren im Canvas:**
   - **Linksklick + Drag:** Neue Box zeichnen (nur wenn keine Box ausgewählt)
   - **Hover + Klick auf Rand:** Box auswählen (preselect)
   - **Zieh-Punkte (Handles):** Skalieren
   - **Drag im Inneren:** Verschieben
   - **Entf-Taste:** Löschen
   - **Mausrad:** Zoomen (um Cursor)
   - **Rechtsklick + Drag:** Panning
5. **Speichern:**
   - **Datei → Speichern** erstellt automatisch `projects/<video_name>_boxes.json`

---

## 💾 Projektliste (Startscreen)

- Listet alle vorhandenen `*_boxes.json` nach Änderungsdatum.
- Doppelklick öffnet die Session.

---

## 🛠️ Erweiterungen

- **Polygon-Annotation** (geplant)
- **KI-basierte Autobox-Generierung** (z.B. YOLOv8)
- **Frame-Navigation & Tracking** (SORT, DeepSORT)

---

## 📄 Lizenz

Dieses Projekt steht unter 🎀 MIT-Lizenz.

