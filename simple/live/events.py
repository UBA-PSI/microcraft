"""
MicroCraft Events - Live Coding
===============================

Lernziel: Inversion of Control (IoC) mit EventBus

Das Problem: CombatSystem muss wissen, wenn eine Einheit stirbt,
damit Explosionen, Sounds, Logs etc. passieren können.

Naive Lösung (schlecht):
    # In CombatSystem:
    if target.hp <= 0:
        particle_system.explode(...)  # Tight coupling!
        sound_manager.play(...)       # Noch mehr coupling!
        logger.log(...)               # Immer schlimmer...

Elegante Lösung: EventBus
    # CombatSystem publiziert nur ein Event:
    event_bus.publish(DeathEvent(...))

    # Handler registrieren sich selbst:
    event_bus.subscribe(DeathEvent, explosion_handler.on_death)
    event_bus.subscribe(DeathEvent, sound_handler.on_death)

Der Clou: CombatSystem weiß NICHTS von den Handlern!
"""
from dataclasses import dataclass
from typing import Callable, Dict, List, Any


# TODO: SpawnEvent Dataclass
#   - kind: str (z.B. "Worker", "Soldier")
#   - entity_id: int
#   - team: int
#   - pos: tuple


# TODO: DeathEvent Dataclass
#   - entity_id: int
#   - kind: str
#   - team: int
#   - pos: tuple


# TODO: ResourceCollectedEvent Dataclass
#   - worker_id: int
#   - team: int
#   - amount: int
#   - team_total: int


# TODO: EventBus Klasse
#   - __init__: self._subscribers = {}
#   - subscribe(event_type, handler): Handler registrieren
#   - publish(event): Alle Handler für diesen Event-Typ aufrufen


# TODO: Globale EventBus Instanz
# event_bus = EventBus()
