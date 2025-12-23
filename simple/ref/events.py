"""
MicroCraft Events - Referenzimplementierung

Dieses Modul zeigt Inversion of Control mit dem EventBus-Pattern.
Systeme publizieren Events, Handler abonnieren und reagieren darauf.
"""
from dataclasses import dataclass
from typing import Callable, Dict, List, Any


# === Event Dataclasses ===
# Using @dataclass for clean, simple event definitions


@dataclass
class SpawnEvent:
    """Fired when a new entity is created.

    Used by: ProductionSystem, Game.setup()
    Handled by: LoggerHandler, HudHandler
    """
    kind: str          # "Worker", "Soldier", "Base", "Barracks"
    entity_id: int
    team: int
    pos: tuple         # (x, y)


@dataclass
class DeathEvent:
    """Fired when an entity dies.

    Used by: CombatSystem
    Handled by: FestiveExplosionHandler, SoundHandler (audio.py), LoggerHandler
    """
    entity_id: int
    kind: str          # "Worker", "Soldier", "Base", "Barracks"
    team: int
    pos: tuple         # (x, y)


@dataclass
class ResourceCollectedEvent:
    """Fired when a worker delivers minerals to base.

    Used by: ResourceSystem
    Handled by: HudHandler, LoggerHandler
    """
    worker_id: int
    team: int
    amount: int        # How many minerals delivered
    team_total: int    # Team's new total


@dataclass
class AttackEvent:
    """Fired when a unit attacks.

    Used by: CombatSystem
    Handled by: SoundHandler (for shooting sounds)
    """
    attacker_id: int
    target_id: int
    team: int
    pos: tuple         # (x, y) of attacker


@dataclass
class CommandEvent:
    """Fired when player issues a command to a unit.

    Used by: Game.issue_command()
    Handled by: SoundHandler (for command acknowledgment)
    """
    entity_id: int
    team: int


@dataclass
class GatherStartEvent:
    """Fired when a worker starts gathering from a mineral patch.

    Used by: ResourceSystem
    Handled by: SoundHandler (for mining sound)
    """
    worker_id: int
    team: int
    pos: tuple         # (x, y) of mineral


# === EventBus ===
# The central dispatcher that connects publishers to subscribers


class EventBus:
    """Central event dispatcher - the heart of IoC pattern.

    Systems call publish() to announce events.
    Handlers call subscribe() to react to events.

    The key insight: Publishers don't know about subscribers!
    Adding new behavior (like Christmas explosions) requires
    NO changes to existing code.
    """

    def __init__(self):
        # Maps event type -> list of handler functions
        self._subscribers: Dict[type, List[Callable]] = {}

    def subscribe(self, event_type: type, handler: Callable) -> None:
        """Register a handler for an event type.

        Args:
            event_type: The class of events to listen for (e.g., DeathEvent)
            handler: A callable that takes the event as its argument
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: type, handler: Callable) -> None:
        """Remove a handler from an event type."""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(handler)
            except ValueError:
                pass  # Handler wasn't subscribed

    def publish(self, event: Any) -> None:
        """Notify all handlers subscribed to this event's type.

        Args:
            event: An event instance (e.g., DeathEvent(...))
        """
        event_type = type(event)
        for handler in self._subscribers.get(event_type, []):
            handler(event)


# === Global EventBus Instance ===
# Used by all systems and handlers in the game

event_bus = EventBus()
