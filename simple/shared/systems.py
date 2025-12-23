"""
Game Systems
Pre-built systems that use the live-coded entities and events.
"""
import math
from typing import TYPE_CHECKING
from .config import (
    TEAM_PLAYER, TEAM_AI, UNIT_STATS, BUILDING_STATS,
    MINERAL_GATHER_AMOUNT, MINERAL_GATHER_TIME, MINERAL_RETURN_RANGE,
    AI_THINK_INTERVAL, SIM_HZ
)
from .commands import MoveTo, AttackMove, Attack, Gather, ReturnResources, Produce

if TYPE_CHECKING:
    from .world import World


class MovementSystem:
    """Moves units toward their destinations"""

    def update(self, world: 'World', dt: float) -> None:
        from ..live.entities import Unit

        for entity in list(world.entities.values()):
            if not isinstance(entity, Unit) or not entity.alive:
                continue

            if entity.destination is None:
                continue

            # Calculate direction to destination
            dx = entity.destination[0] - entity.x
            dy = entity.destination[1] - entity.y
            dist = math.sqrt(dx * dx + dy * dy)

            if dist < 0.1:
                # Arrived
                entity.destination = None
                continue

            # Normalize and apply speed
            move_dist = entity.speed * dt
            if move_dist >= dist:
                # Will arrive this frame
                entity.x = entity.destination[0]
                entity.y = entity.destination[1]
                entity.destination = None
            else:
                # Move toward destination
                entity.x += (dx / dist) * move_dist
                entity.y += (dy / dist) * move_dist


class CombatSystem:
    """Handles combat between units"""

    def update(self, world: 'World', dt: float) -> None:
        from ..live.entities import Soldier
        from ..live.events import event_bus, DeathEvent, AttackEvent

        for entity in list(world.entities.values()):
            if not isinstance(entity, Soldier) or not entity.alive:
                continue

            # Reduce cooldown
            if entity.cooldown > 0:
                entity.cooldown -= dt
                continue

            # Find target
            target = None
            if entity.target:
                target = world.get_entity(entity.target)
                if target and not target.alive:
                    entity.target = None
                    target = None

            # Auto-acquire nearest enemy if no target
            if target is None:
                target = world.get_nearest_enemy(entity, entity.attack_range)
                if target:
                    entity.target = target.id

            if target is None:
                continue

            # Check range
            dx = target.x - entity.x
            dy = target.y - entity.y
            dist = math.sqrt(dx * dx + dy * dy)

            if dist > entity.attack_range:
                # Move toward target
                entity.destination = (target.x, target.y)
                continue

            # Attack!
            target.hp -= entity.damage
            entity.cooldown = UNIT_STATS["Soldier"]["cooldown"]

            # Publish attack event (for sound effects)
            event_bus.publish(AttackEvent(
                attacker_id=entity.id,
                target_id=target.id,
                team=entity.team,
                pos=(entity.x, entity.y)
            ))

            # Check for death
            if target.hp <= 0:
                target.alive = False
                entity.target = None

                # Publish death event
                kind = type(target).__name__
                event_bus.publish(DeathEvent(
                    entity_id=target.id,
                    kind=kind,
                    team=target.team,
                    pos=(target.x, target.y)
                ))

                # Remove from world
                world.remove_entity(target.id)


class ResourceSystem:
    """Handles worker gathering and resource delivery"""

    def __init__(self):
        self.gather_timers = {}  # worker_id -> time remaining

    def update(self, world: 'World', dt: float) -> None:
        from ..live.entities import Worker, Base
        from ..live.events import event_bus, ResourceCollectedEvent, GatherStartEvent

        for entity in list(world.entities.values()):
            if not isinstance(entity, Worker) or not entity.alive:
                continue

            # If carrying resources, head to base
            if entity.carrying > 0:
                base = world.get_base(entity.team)
                if base:
                    # Check if close enough to drop off
                    dx = base.x - entity.x
                    dy = base.y - entity.y
                    dist = math.sqrt(dx * dx + dy * dy)

                    if dist <= MINERAL_RETURN_RANGE:
                        # Deliver resources
                        world.add_minerals(entity.team, entity.carrying)
                        total = world.get_minerals(entity.team)

                        event_bus.publish(ResourceCollectedEvent(
                            worker_id=entity.id,
                            team=entity.team,
                            amount=entity.carrying,
                            team_total=total
                        ))

                        entity.carrying = 0
                        # Go back to mineral patch
                        if entity.gather_target:
                            entity.destination = (entity.gather_target.x, entity.gather_target.y)
                    else:
                        # Move to base
                        entity.destination = (base.x, base.y)
                continue

            # If has a gather target, move to it and gather
            if entity.gather_target:
                mineral = entity.gather_target
                if mineral.depleted:
                    # Find new mineral
                    entity.gather_target = world.game_map.get_nearest_mineral(entity.x, entity.y)
                    if entity.gather_target:
                        entity.destination = (entity.gather_target.x, entity.gather_target.y)
                    continue

                # Check if close enough to gather
                dx = mineral.x - entity.x
                dy = mineral.y - entity.y
                dist = math.sqrt(dx * dx + dy * dy)

                if dist <= 1.5:
                    # Gathering
                    if entity.id not in self.gather_timers:
                        self.gather_timers[entity.id] = MINERAL_GATHER_TIME
                        # Publish gather start event (for mining sound)
                        event_bus.publish(GatherStartEvent(
                            worker_id=entity.id,
                            team=entity.team,
                            pos=(mineral.x, mineral.y)
                        ))

                    self.gather_timers[entity.id] -= dt

                    if self.gather_timers[entity.id] <= 0:
                        # Harvest complete
                        amount = mineral.harvest(MINERAL_GATHER_AMOUNT)
                        entity.carrying = amount
                        del self.gather_timers[entity.id]
                else:
                    # Move to mineral
                    entity.destination = (mineral.x, mineral.y)


class ProductionSystem:
    """Handles building production queues"""

    def update(self, world: 'World', dt: float) -> None:
        from ..live.entities import Building, Base, Barracks, Worker, Soldier
        from ..live.events import event_bus, SpawnEvent

        for entity in list(world.entities.values()):
            if not isinstance(entity, Building) or not entity.alive:
                continue

            if entity.current_production is None:
                continue

            # Get production time
            unit_type = entity.current_production
            if unit_type == "Worker":
                build_time = UNIT_STATS["Worker"]["build_time"]
            elif unit_type == "Soldier":
                build_time = UNIT_STATS["Soldier"]["build_time"]
            else:
                continue

            # Progress production
            entity.production_progress += dt / build_time

            if entity.production_progress >= 1.0:
                # Production complete - spawn unit
                entity.production_progress = 0.0
                entity.current_production = None

                # Spawn position (next to building)
                spawn_x = entity.x + 2
                spawn_y = entity.y

                # Create the unit
                new_id = world.get_next_id()
                if unit_type == "Worker":
                    new_unit = Worker(new_id, entity.team, (spawn_x, spawn_y))
                else:
                    new_unit = Soldier(new_id, entity.team, (spawn_x, spawn_y))

                world.add_entity(new_unit)

                # Publish spawn event
                event_bus.publish(SpawnEvent(
                    kind=unit_type,
                    entity_id=new_id,
                    team=entity.team,
                    pos=(spawn_x, spawn_y)
                ))


class AISystem:
    """Simple AI opponent - 3 state machine"""

    def __init__(self):
        self.think_timer = 0.0
        self.state = "build_workers"  # build_workers -> build_barracks -> attack

    def update(self, world: 'World', dt: float) -> None:
        from ..live.entities import Worker, Soldier, Base, Barracks

        self.think_timer += dt
        if self.think_timer < AI_THINK_INTERVAL:
            return
        self.think_timer = 0.0

        # Get AI entities
        workers = [e for e in world.get_units_by_team(TEAM_AI) if isinstance(e, Worker)]
        soldiers = [e for e in world.get_units_by_team(TEAM_AI) if isinstance(e, Soldier)]
        buildings = world.get_buildings_by_team(TEAM_AI)
        base = world.get_base(TEAM_AI)
        barracks = [b for b in buildings if isinstance(b, Barracks)]

        minerals = world.get_minerals(TEAM_AI)

        # State machine
        if self.state == "build_workers":
            # Build workers until we have 5
            if len(workers) < 5 and base:
                if base.current_production is None and minerals >= UNIT_STATS["Worker"]["cost"]:
                    if world.spend_minerals(TEAM_AI, UNIT_STATS["Worker"]["cost"]):
                        base.start_production()

            # Ensure workers are gathering
            for worker in workers:
                if worker.gather_target is None and worker.carrying == 0:
                    mineral = world.game_map.get_nearest_mineral(worker.x, worker.y)
                    if mineral:
                        worker.gather_target = mineral
                        worker.destination = (mineral.x, mineral.y)

            # Transition: have 5 workers
            if len(workers) >= 5:
                self.state = "build_barracks"

        elif self.state == "build_barracks":
            # Build a barracks if we don't have one
            if not barracks:
                if minerals >= BUILDING_STATS["Barracks"]["cost"]:
                    if world.spend_minerals(TEAM_AI, BUILDING_STATS["Barracks"]["cost"]):
                        # Place barracks near base
                        if base:
                            bx, by = base.x + 4, base.y
                            new_id = world.get_next_id()
                            new_barracks = Barracks(new_id, TEAM_AI, (bx, by))
                            world.add_entity(new_barracks)

                            from ..live.events import event_bus, SpawnEvent
                            event_bus.publish(SpawnEvent(
                                kind="Barracks",
                                entity_id=new_id,
                                team=TEAM_AI,
                                pos=(bx, by)
                            ))
            else:
                # Have barracks, build soldiers
                my_barracks = barracks[0]
                if my_barracks.current_production is None and minerals >= UNIT_STATS["Soldier"]["cost"]:
                    if world.spend_minerals(TEAM_AI, UNIT_STATS["Soldier"]["cost"]):
                        my_barracks.start_production()

                # Transition: have 6 soldiers
                if len(soldiers) >= 6:
                    self.state = "attack"

            # Keep workers gathering
            for worker in workers:
                if worker.gather_target is None and worker.carrying == 0:
                    mineral = world.game_map.get_nearest_mineral(worker.x, worker.y)
                    if mineral:
                        worker.gather_target = mineral
                        worker.destination = (mineral.x, mineral.y)

        elif self.state == "attack":
            # Attack the player base
            player_base = world.get_base(TEAM_PLAYER)
            if player_base:
                target_pos = (player_base.x, player_base.y)
                for soldier in soldiers:
                    if soldier.destination is None:
                        soldier.destination = target_pos
                        soldier.target = player_base.id

            # Keep building soldiers
            if barracks:
                my_barracks = barracks[0]
                if my_barracks.current_production is None and minerals >= UNIT_STATS["Soldier"]["cost"]:
                    if world.spend_minerals(TEAM_AI, UNIT_STATS["Soldier"]["cost"]):
                        my_barracks.start_production()

            # Keep workers gathering
            for worker in workers:
                if worker.gather_target is None and worker.carrying == 0:
                    mineral = world.game_map.get_nearest_mineral(worker.x, worker.y)
                    if mineral:
                        worker.gather_target = mineral
                        worker.destination = (mineral.x, mineral.y)


class BuildingPlacementSystem:
    """Handles worker building construction (simple version)

    Workers with build_target will move to the location and construct.
    In full mode this is more complex with validation and events.
    Here we keep it minimal for the lecture.
    """

    def __init__(self):
        self._build_timers = {}  # worker_id -> elapsed_time
        self._last_mineral_warning = 0.0  # Timestamp of last warning

    def update(self, world: 'World', dt: float) -> None:
        from ..live.entities import Worker, Barracks
        from ..live.events import event_bus, SpawnEvent

        # Clean up timers for workers that no longer exist
        stale_ids = [wid for wid in self._build_timers if wid not in world.entities]
        for wid in stale_ids:
            del self._build_timers[wid]

        for entity in list(world.entities.values()):
            if not isinstance(entity, Worker) or not entity.alive:
                # Clean up timer for dead workers
                if entity.id in self._build_timers:
                    del self._build_timers[entity.id]
                continue

            if not hasattr(entity, 'build_target') or entity.build_target is None:
                continue

            building_type, bx, by = entity.build_target

            # Move to build site
            dx = bx - entity.x
            dy = by - entity.y
            dist = math.sqrt(dx * dx + dy * dy)

            if dist > 2.0:
                entity.destination = (bx, by)
                continue

            # At build site - stop moving
            entity.destination = None

            # Check if we can afford it
            cost = BUILDING_STATS[building_type]["cost"]
            current = world.get_minerals(entity.team)
            if current < cost:
                # Cancel build and warn player (max once per second)
                if entity.team == TEAM_PLAYER:
                    if world.game_time - self._last_mineral_warning >= 1.0:
                        print(f"Not enough minerals for {building_type}! Need {cost}, have {current}")
                        self._last_mineral_warning = world.game_time
                # Cancel the build attempt - worker goes idle
                entity.build_target = None
                continue

            # Progress building timer
            if entity.id not in self._build_timers:
                self._build_timers[entity.id] = 0.0

            self._build_timers[entity.id] += dt
            build_time = BUILDING_STATS[building_type]["build_time"]

            if self._build_timers[entity.id] >= build_time:
                # Construction complete! Spend minerals first (already checked above)
                if not world.spend_minerals(entity.team, cost):
                    # Minerals were spent elsewhere during build - cancel
                    entity.build_target = None
                    del self._build_timers[entity.id]
                    continue

                # Create building
                new_id = world.get_next_id()
                new_building = Barracks(new_id, entity.team, (int(bx), int(by)))
                world.add_entity(new_building)

                # Publish event
                event_bus.publish(SpawnEvent(
                    kind=building_type,
                    entity_id=new_id,
                    team=entity.team,
                    pos=(int(bx), int(by))
                ))

                # Clear build task
                entity.build_target = None
                del self._build_timers[entity.id]
