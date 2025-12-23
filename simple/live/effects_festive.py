"""
MicroCraft Festive Effects - Live Coding
========================================

Hier sieht man IoC in Aktion:
Weihnachts-Explosionen werden hinzugefügt, ohne eine
einzige Zeile im CombatSystem zu ändern.

Funktionsweise:
1. FestiveExplosionHandler bekommt particle_system im Konstruktor
2. Handler registriert sich selbst beim EventBus für DeathEvent
3. Wenn eine Einheit stirbt, wird on_death() automatisch aufgerufen
4. Handler spawnt bunte Partikel

Das CombatSystem weiß nichts davon - Zero Coupling.
"""
import random
from .events import event_bus, DeathEvent


# TODO: FestiveExplosionHandler Klasse
#
# COLORS = ["#FF0000", "#00FF00", "#FFD700", "#FFFFFF", "#FF69B4", "#00CED1"]
#
# __init__(self, particle_system):
#     - self.particles speichern
#     - event_bus.subscribe(DeathEvent, self.on_death)  # <- Die Magie!
#
# on_death(self, event: DeathEvent):
#     - Position aus event.pos extrahieren
#     - self.particles.spawn_burst(...) aufrufen
#     - Optionale Sparkles mit self.particles.spawn(...)
