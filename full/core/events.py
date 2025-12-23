"""
MicroCraft Full Events - Complete Implementation

All 6 event types for the full RTS experience.
"""
from dataclasses import dataclass
from typing import Callable, Dict, List, Any


# === Event Dataclasses ===

@dataclass
class SpawnEvent:
    """Fired when a new entity is created."""
    kind: str
    entity_id: int
    team: int
    pos: tuple


@dataclass
class DeathEvent:
    """Fired when an entity dies."""
    entity_id: int
    kind: str
    team: int
    pos: tuple
    killer_id: int = None  # Who killed this entity


@dataclass
class ResourceCollectedEvent:
    """Fired when a worker delivers minerals to base."""
    worker_id: int
    team: int
    amount: int
    team_total: int


@dataclass
class GatheringStartedEvent:
    """Fired when a worker starts mining minerals."""
    worker_id: int
    team: int


@dataclass
class ProductionStartedEvent:
    """Fired when a building starts producing a unit."""
    building_id: int
    unit_type: str
    team: int
    queue_position: int


@dataclass
class ProductionCompletedEvent:
    """Fired when a building completes a unit."""
    building_id: int
    unit_type: str
    unit_id: int
    team: int
    pos: tuple


@dataclass
class BuildingPlacedEvent:
    """Fired when a worker places a new building."""
    building_id: int
    building_type: str
    team: int
    pos: tuple
    builder_id: int


@dataclass
class CommandEvent:
    """Fired when player issues a command to a unit."""
    entity_id: int
    team: int


@dataclass
class AttackEvent:
    """Fired when a unit attacks another."""
    attacker_id: int
    target_id: int
    damage: int
    target_hp_remaining: int


@dataclass
class VisibilityChangedEvent:
    """Fired when fog of war reveals/hides entities."""
    entity_id: int
    team: int
    now_visible: bool


@dataclass
class EnemySpottedEvent:
    """Fired when a soldier spots an enemy entity."""
    soldier_id: int
    team: int
    enemy_id: int
    enemy_pos: tuple
    is_base: bool  # True if enemy base was spotted


@dataclass
class ReinforcementRequestedEvent:
    """Fired when a soldier requests backup at a location."""
    soldier_id: int
    team: int
    target_pos: tuple


@dataclass
class MineDepletedEvent:
    """Fired when a worker's mine becomes depleted."""
    worker_id: int
    team: int
    mine_pos: tuple


@dataclass
class BaseUnderAttackEvent:
    """Fired when a team's base is being attacked."""
    base_id: int
    team: int
    attacker_id: int


@dataclass
class AIDecisionEvent:
    """Fired when the AI makes a decision (for logging)."""
    team: int
    decision_type: str  # e.g., "state_change", "build_worker", "build_barracks", etc.
    message: str        # Human-readable explanation
    details: dict = None  # Optional additional data


@dataclass
class BuildingConstructionStartEvent:
    """Fired when a worker starts building construction."""
    worker_id: int
    team: int
    building_type: str
    pos: tuple


@dataclass
class BuildingConstructionProgressEvent:
    """Fired to update building construction progress."""
    worker_id: int
    team: int
    building_type: str
    pos: tuple
    progress: float  # 0.0 to 1.0


@dataclass
class InsufficientMineralsEvent:
    """Fired when trying to queue production without enough minerals."""
    team: int
    building_id: int
    unit_type: str
    cost: int
    available: int


@dataclass
class WorkerWaitingForMineralsEvent:
    """Fired when worker is waiting for minerals to build."""
    worker_id: int
    team: int
    building_type: str
    cost: int


@dataclass
class UnitReadyEvent:
    """Fired when a new unit announces itself."""
    unit_id: int
    unit_type: str
    team: int
    name: str
    rank: str = None  # Only for soldiers


# === EventBus ===

class EventBus:
    """Central event dispatcher - the heart of IoC pattern."""

    def __init__(self):
        self._subscribers: Dict[type, List[Callable]] = {}
        self._event_history: List[Any] = []  # For debugging/replay
        self._recording = False

    def subscribe(self, event_type: type, handler: Callable) -> None:
        """Register a handler for an event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: type, handler: Callable) -> None:
        """Remove a handler from an event type."""
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(handler)
            except ValueError:
                pass

    def publish(self, event: Any) -> None:
        """Notify all handlers subscribed to this event's type."""
        if self._recording:
            self._event_history.append(event)

        event_type = type(event)
        for handler in self._subscribers.get(event_type, []):
            handler(event)

    def clear(self) -> None:
        """Clear all subscribers."""
        self._subscribers.clear()

    def start_recording(self) -> None:
        """Start recording events for replay/debugging."""
        self._recording = True
        self._event_history.clear()

    def stop_recording(self) -> List[Any]:
        """Stop recording and return event history."""
        self._recording = False
        return self._event_history.copy()


# Global EventBus instance
event_bus = EventBus()
