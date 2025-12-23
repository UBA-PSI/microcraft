"""
Commands
Command objects that can be issued to units and buildings.
Both player and AI use the same command types.
"""
from dataclasses import dataclass
from typing import Tuple, Optional


@dataclass
class MoveTo:
    """Move to a position"""
    target_pos: Tuple[float, float]


@dataclass
class AttackMove:
    """Move toward position, engaging enemies on the way"""
    target_pos: Tuple[float, float]


@dataclass
class Attack:
    """Attack a specific target"""
    target_id: int


@dataclass
class Gather:
    """Gather from a mineral patch"""
    mineral_x: int
    mineral_y: int


@dataclass
class ReturnResources:
    """Return carried resources to base"""
    base_id: int


@dataclass
class Build:
    """Build a structure at position"""
    building_type: str
    pos: Tuple[int, int]


@dataclass
class Produce:
    """Produce a unit (issued to building)"""
    unit_type: str


# Type alias for any command
Command = MoveTo | AttackMove | Attack | Gather | ReturnResources | Build | Produce
