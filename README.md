# MicroCraft

Ein minimales Echtzeit-Strategiespiel im StarCraft-Stil zum Erlernen von OOP-Konzepten in Python.

## Schnellstart

```bash
# Virtuelle Umgebung aktivieren
source venv/bin/activate  # macOS/Linux
# oder: venv\Scripts\activate  # Windows

# Abhängigkeiten installieren
pip install -r requirements.txt

# Simple Version starten (Live-Coding)
python -m simple.main --use-ref

# Full Version starten (Feature-komplett)
python -m full.main
```

## Projektstruktur

```
microcraft/
├── simple/          # Live-Coding Version (90min Vorlesung)
│   ├── live/        # TODOs für Vorlesung (wird live gecodet)
│   ├── ref/         # Referenz-Implementierungen
│   └── shared/      # Fertige Infrastruktur
├── full/            # Feature-komplette Version
│   └── core/        # A*, Fog of War, 5-State AI
├── frontends/       # Renderer (Duck Typing Demo)
│   ├── pygame_renderer.py   # Mit Sprites
│   └── simple_renderer.py   # Mit Kreisen/Rechtecken
├── data/            # JSON/CSV Konfiguration
└── assets/          # Grafik/Audio
```

## Steuerung

| Taste | Aktion |
|-------|--------|
| WASD / Pfeiltasten | Kamera bewegen |
| Linksklick | Auswählen / Befehl geben |
| Q | Produktion starten |
| B | Gebäude bauen (Worker ausgewählt) |
| ESC | Beenden |

## Lernziele

Das Projekt demonstriert drei OOP-Konzepte:

1. **Vererbung** (30min): `Entity` → `Unit` → `Worker`/`Soldier`
   - Datei: `simple/live/entities.py`

2. **Duck Typing** (20min): `PygameRenderer` vs `SimpleRenderer`
   - Keine gemeinsame Basisklasse, gleiches Interface

3. **Inversion of Control** (25min): `EventBus` + Handler
   - Dateien: `simple/live/events.py`, `simple/live/effects_festive.py`

Siehe [LIVECODING_SCRIPT.md](LIVECODING_SCRIPT.md) für detaillierte Anweisungen.

## Kommandozeilen-Optionen

```bash
# Simple Version (immer SimpleRenderer - Kreise/Rechtecke)
python -m simple.main              # Nutzt live/ (für Vorlesung)
python -m simple.main --use-ref    # Nutzt ref/ (für Demo)

# Full Version
python -m full.main                # Pygame GUI mit Sprites
python -m full.main --verbose      # Mit Event-Log
python -m full.main --debug        # Kein Fog of War, AI-Log
python -m full.main --xmas         # Festliche Explosionen
python -m full.main --simple-renderer  # Mit SimpleRenderer

# Oder via run.sh:
./run.sh simple --ref              # Simple + Referenz-Impl
./run.sh full                      # Full Version mit Sprites
./run.sh full --debug              # Full + Debug-Modus
./run.sh full --xmas               # Full + Weihnachts-Effekte
```

## Tests

```bash
python -m pytest tests/ -v
```

## Audio

### Musik

Music by **Scott Buckley** - CC-BY 4.0 - https://www.scottbuckley.com.au

Die Musik ist im Repository enthalten und kann weiterverbreitet werden.

### Sound-Effekte

Sound-Effekte von **Shapeforms Audio** sind **NICHT im Repository enthalten** (Lizenz erlaubt keine Open-Source-Redistribution).

Setup:
1. Download von https://shapeforms.itch.io/shapeforms-audio-free-sfx
2. `.wav`-Dateien direkt in `assets/sounds/sfx/` kopieren (keine Unterordner)

Details siehe `assets/sounds/sfx/README.md`.

## Credits

### Code
Entwickelt mit **Claude Code** (Anthropic)

### Grafik
Sprites generiert mit **Google Imagen 3** (Nano Banana Pro)

### Audio
- **Musik**: Scott Buckley - CC-BY 4.0 - https://www.scottbuckley.com.au
- **Sound-Effekte**: Shapeforms Audio - https://shapeforms.itch.io/shapeforms-audio-free-sfx

## Dokumentation

Siehe [spec.md](spec.md) für die vollständige Spezifikation.
