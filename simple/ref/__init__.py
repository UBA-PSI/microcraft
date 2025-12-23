"""
MicroCraft Simple - Reference Implementations
Complete implementations of the live-coded files.
Copy these to simple/live/ to skip live-coding during testing.
"""
from .entities import Entity, Unit, Worker, Soldier, Building, Base, Barracks
from .events import EventBus, event_bus, SpawnEvent, DeathEvent, ResourceCollectedEvent
from .effects_festive import FestiveExplosionHandler, LoggerHandler
from .audio import SoundHandler, NullAudioHandler
