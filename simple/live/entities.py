"""
MicroCraft Entities - Live Coding
=================================

Lernziel: Vererbung mit super().__init__()

Wir implementieren eine Klassenhierarchie:
    Entity (Basis)
    ├── Unit (beweglich)
    │   ├── Worker (sammelt Ressourcen)
    │   └── Soldier (kämpft)
    └── Building (statisch)
        ├── Base (produziert Worker)
        └── Barracks (produziert Soldiers)
"""
from ..shared.config import UNIT_STATS, BUILDING_STATS


# TODO: Entity Basisklasse
#   - __init__(self, entity_id, team, pos, hp)
#   - Attribute: id, team, x, y, hp, max_hp, alive
#   - Methode: take_damage(amount)


# TODO: Unit(Entity) - bewegliche Einheiten
#   - __init__ mit super().__init__()
#   - Zusätzlich: speed, destination, target


# TODO: Worker(Unit) - Ressourcensammler
#   - Stats aus UNIT_STATS["Worker"] laden
#   - Zusätzlich: carrying, gather_target, vision, state, build_target


# TODO: Soldier(Unit) - Kampfeinheit
#   - Stats aus UNIT_STATS["Soldier"] laden
#   - Zusätzlich: damage, attack_range, cooldown


# TODO: Building(Entity) - statische Gebäude
#   - Zusätzlich: current_production, production_progress


# TODO: Base(Building) - Hauptgebäude
#   - Stats aus BUILDING_STATS["Base"] laden
#   - Methode: start_production() -> startet Worker


# TODO: Barracks(Building) - Kaserne
#   - Stats aus BUILDING_STATS["Barracks"] laden
#   - Methode: start_production() -> startet Soldier
