"""
MicroCraft Full Systems - Complete Implementation

Advanced features:
- A* Pathfinding
- 5-state AI
- Production Queues
- Fog of War updates
"""
import heapq
import math
import random
from typing import List, Optional, Tuple, Dict, Set

from .entities import Entity, Unit, Worker, Soldier, Building, Base, Barracks, UNIT_STATS, BUILDING_STATS
from .events import (
    event_bus,
    DeathEvent,
    ResourceCollectedEvent,
    ProductionStartedEvent,
    ProductionCompletedEvent,
    BuildingPlacedEvent,
    AttackEvent,
    MineDepletedEvent,
    BaseUnderAttackEvent,
    AIDecisionEvent,
    BuildingConstructionStartEvent,
    BuildingConstructionProgressEvent,
    InsufficientMineralsEvent,
    WorkerWaitingForMineralsEvent,
    UnitReadyEvent,
    GatheringStartedEvent,
)
from .effects import WORKER_NAMES, SOLDIER_RANKS


class PathFinder:
    """A* pathfinding with 8-directional movement."""

    # 8-directional movement with costs
    DIRECTIONS = [
        ((-1, -1), 1.414),  # Diagonal
        ((0, -1), 1.0),
        ((1, -1), 1.414),
        ((-1, 0), 1.0),
        ((1, 0), 1.0),
        ((-1, 1), 1.414),
        ((0, 1), 1.0),
        ((1, 1), 1.414),
    ]

    def __init__(self, game_map):
        self.game_map = game_map

    def find_path(self, start: Tuple[float, float], goal: Tuple[float, float]) -> List[Tuple[int, int]]:
        """Find optimal path from start to goal using A*."""
        if not self.game_map:
            return [goal]

        start = (int(start[0]), int(start[1]))
        goal = (int(goal[0]), int(goal[1]))

        if start == goal:
            return []

        # Check if goal is walkable, if not find nearest walkable
        if not self.game_map.is_walkable(goal[0], goal[1]):
            goal = self._find_nearest_walkable(goal)
            if goal is None:
                return []

        # A* algorithm
        open_set: List[Tuple[float, int, Tuple[int, int]]] = [(0, 0, start)]
        came_from: Dict[Tuple[int, int], Tuple[int, int]] = {}
        g_score: Dict[Tuple[int, int], float] = {start: 0}
        counter = 0  # Tie-breaker for heap

        while open_set:
            _, _, current = heapq.heappop(open_set)

            if current == goal:
                return self._reconstruct_path(came_from, current)

            for (dx, dy), cost in self.DIRECTIONS:
                neighbor = (current[0] + dx, current[1] + dy)

                if not self.game_map.is_walkable(neighbor[0], neighbor[1]):
                    continue

                tentative_g = g_score[current] + cost

                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score = tentative_g + self._heuristic(neighbor, goal)
                    counter += 1
                    heapq.heappush(open_set, (f_score, counter, neighbor))

        # No path found
        return []

    def _heuristic(self, a: Tuple[int, int], b: Tuple[int, int]) -> float:
        """Diagonal distance heuristic."""
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        return max(dx, dy) + 0.414 * min(dx, dy)

    def _reconstruct_path(self, came_from: Dict, current: Tuple[int, int]) -> List[Tuple[int, int]]:
        """Reconstruct path from came_from dict."""
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path[1:]  # Exclude start position

    def _find_nearest_walkable(self, pos: Tuple[int, int]) -> Optional[Tuple[int, int]]:
        """Find nearest walkable tile to given position."""
        for radius in range(1, 10):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if abs(dx) == radius or abs(dy) == radius:
                        nx, ny = pos[0] + dx, pos[1] + dy
                        if self.game_map.is_walkable(nx, ny):
                            return (nx, ny)
        return None


class MovementSystem:
    """Handles unit movement with pathfinding and collision detection."""

    STUCK_THRESHOLD = 16.0  # Seconds before considering unit stuck
    STUCK_MOVE_DISTANCE = 0.3  # Minimum movement to not be considered stuck

    def __init__(self, world):
        self.world = world
        self.pathfinder = None
        # Track stuck timers: entity_id -> (timer, last_x, last_y)
        self._stuck_timers: Dict[int, Tuple[float, float, float]] = {}

    def _is_walkable(self, x: float, y: float) -> bool:
        """Check if position is walkable."""
        if not self.world.game_map:
            return True
        return self.world.game_map.is_walkable(int(x), int(y))

    def update(self, dt: float) -> None:
        """Move all units toward their destinations."""
        if self.pathfinder is None and self.world.game_map:
            self.pathfinder = PathFinder(self.world.game_map)

        for entity in self.world.entities.values():
            if not isinstance(entity, Unit) or not entity.alive:
                # Clean up stuck timer for dead units
                if entity.id in self._stuck_timers:
                    del self._stuck_timers[entity.id]
                continue

            # Track stuck detection
            self._update_stuck_detection(entity, dt)

            # Use path if available
            if entity.path:
                next_waypoint = entity.path[0]
                dx = next_waypoint[0] - entity.x
                dy = next_waypoint[1] - entity.y
                dist = math.sqrt(dx * dx + dy * dy)

                if dist < 0.5:
                    entity.path.pop(0)
                    continue

                # Move toward waypoint with collision check
                if dist > 0:
                    # Update facing angle (0 = right, 90 = up)
                    entity.angle = math.degrees(math.atan2(-dy, dx))

                    move_dist = entity.speed * dt
                    new_x = entity.x + (dx / dist) * min(move_dist, dist)
                    new_y = entity.y + (dy / dist) * min(move_dist, dist)

                    # Only move if target is walkable
                    if self._is_walkable(new_x, new_y):
                        entity.x = new_x
                        entity.y = new_y
                    else:
                        # Path blocked, recalculate
                        entity.path = []
                        if entity.destination and self.pathfinder:
                            entity.path = self.pathfinder.find_path(
                                (entity.x, entity.y),
                                entity.destination
                            )

            elif entity.destination:
                dx = entity.destination[0] - entity.x
                dy = entity.destination[1] - entity.y
                dist = math.sqrt(dx * dx + dy * dy)

                if dist < 0.5:
                    entity.destination = None
                    continue

                # Update facing angle toward destination
                entity.angle = math.degrees(math.atan2(-dy, dx))

                # Always use pathfinding for movement
                if self.pathfinder:
                    entity.path = self.pathfinder.find_path(
                        (entity.x, entity.y),
                        entity.destination
                    )
                    if not entity.path:
                        # No valid path, clear destination
                        entity.destination = None

    def _update_stuck_detection(self, entity: Unit, dt: float) -> None:
        """Check if unit is stuck and unstick if needed."""
        # Only check units that have a destination or path
        if not entity.destination and not entity.path:
            # Unit is idle, reset stuck timer
            if entity.id in self._stuck_timers:
                del self._stuck_timers[entity.id]
            return

        # Get or initialize stuck tracking data
        if entity.id not in self._stuck_timers:
            self._stuck_timers[entity.id] = (0.0, entity.x, entity.y)
            return

        timer, last_x, last_y = self._stuck_timers[entity.id]

        # Check if unit has moved significantly
        dx = entity.x - last_x
        dy = entity.y - last_y
        dist_moved = math.sqrt(dx * dx + dy * dy)

        if dist_moved > self.STUCK_MOVE_DISTANCE:
            # Unit is moving, reset timer
            self._stuck_timers[entity.id] = (0.0, entity.x, entity.y)
        else:
            # Unit hasn't moved, increment timer
            timer += dt
            self._stuck_timers[entity.id] = (timer, last_x, last_y)

            if timer >= self.STUCK_THRESHOLD:
                # Unit is stuck! Try to unstick it
                self._unstick_unit(entity)
                del self._stuck_timers[entity.id]

    def _unstick_unit(self, entity: Unit) -> None:
        """Move a stuck unit to a nearby walkable tile."""
        if not self.world.game_map:
            return

        # Find nearest walkable tile that's different from current position
        current_tile = (int(entity.x), int(entity.y))

        for radius in range(1, 5):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if abs(dx) == radius or abs(dy) == radius:
                        nx, ny = current_tile[0] + dx, current_tile[1] + dy
                        if self.world.game_map.is_walkable(nx, ny):
                            # Check if tile is not occupied by another entity
                            occupied = False
                            for other in self.world.entities.values():
                                if other.id != entity.id and other.alive:
                                    odx = other.x - nx
                                    ody = other.y - ny
                                    if odx * odx + ody * ody < 1.0:
                                        occupied = True
                                        break
                            if not occupied:
                                # Teleport unit to this tile
                                entity.x = float(nx) + 0.5
                                entity.y = float(ny) + 0.5
                                entity.path = []  # Clear path to force recalculation
                                return


class CombatSystem:
    """Handles combat between units."""

    def __init__(self, world):
        self.world = world
        self._base_attack_cooldown = {}  # Track base attack notifications

    def update(self, dt: float) -> None:
        """Process combat for all soldiers."""
        dead_entities = []

        for entity in list(self.world.entities.values()):
            if not isinstance(entity, Soldier) or not entity.alive:
                continue

            # Reduce cooldown
            if entity.cooldown_remaining > 0:
                entity.cooldown_remaining -= dt

            # Find target if none
            if entity.target is None:
                enemies = self.world.get_enemies_in_range(entity, entity.attack_range * 2)
                if enemies:
                    entity.target = min(enemies, key=lambda e: (e.x - entity.x)**2 + (e.y - entity.y)**2).id

            # Process target
            if entity.target:
                target = self.world.get_entity(entity.target)

                if not target or not target.alive:
                    entity.target = None
                    continue

                dx = target.x - entity.x
                dy = target.y - entity.y
                dist = math.sqrt(dx * dx + dy * dy)

                if dist <= entity.attack_range:
                    # In range - attack if cooldown ready
                    entity.destination = None
                    entity.path = []

                    if entity.cooldown_remaining <= 0:
                        target.take_damage(entity.damage)
                        entity.cooldown_remaining = entity.attack_cooldown

                        event_bus.publish(AttackEvent(
                            attacker_id=entity.id,
                            target_id=target.id,
                            damage=entity.damage,
                            target_hp_remaining=target.hp
                        ))

                        # Check if attacking a base - fire alert event
                        if isinstance(target, Base):
                            # Cooldown to avoid spamming alerts
                            base_id = target.id
                            last_alert = self._base_attack_cooldown.get(base_id, 0)
                            current_time = self.world.game_time
                            if current_time - last_alert >= 10.0:  # 10 second cooldown
                                self._base_attack_cooldown[base_id] = current_time
                                event_bus.publish(BaseUnderAttackEvent(
                                    base_id=target.id,
                                    team=target.team,
                                    attacker_id=entity.id
                                ))

                        if not target.alive:
                            dead_entities.append((target, entity.id))
                else:
                    # Move toward target
                    entity.destination = (target.x, target.y)

        # Process deaths
        for target, killer_id in dead_entities:
            event_bus.publish(DeathEvent(
                entity_id=target.id,
                kind=target.kind,
                team=target.team,
                pos=target.pos,
                killer_id=killer_id
            ))


class ResourceSystem:
    """Handles worker resource gathering."""

    GATHER_TIME = 2.0
    GATHER_AMOUNT = 8

    def __init__(self, world):
        self.world = world
        self._gather_timers: Dict[int, float] = {}

    def update(self, dt: float) -> None:
        """Process worker gathering behavior."""
        for entity in list(self.world.entities.values()):
            if not isinstance(entity, Worker) or not entity.alive:
                continue

            self._process_worker(entity, dt)

    def _process_worker(self, worker: Worker, dt: float) -> None:
        """Process a single worker's gathering loop."""
        base = self.world.get_base(worker.team)
        if not base:
            return

        # State machine
        if worker.state == "idle":
            if worker.gather_target:
                worker.state = "moving_to_mineral"
                worker.destination = worker.gather_target.pos
            elif worker.carrying > 0:
                worker.state = "returning"
                worker.destination = base.pos

        elif worker.state == "moving_to_mineral":
            if worker.gather_target is None or worker.gather_target.depleted:
                # Mine is depleted - fire event and wait for player command (for player team)
                if worker.gather_target and worker.gather_target.depleted:
                    mine_pos = worker.gather_target.pos
                    worker.gather_target = None
                    worker.destination = None
                    worker.state = "idle"
                    # Fire mine depleted event
                    event_bus.publish(MineDepletedEvent(
                        worker_id=worker.id,
                        team=worker.team,
                        mine_pos=mine_pos
                    ))
                else:
                    worker.state = "idle"
                return

            dx = worker.gather_target.x - worker.x
            dy = worker.gather_target.y - worker.y
            if dx * dx + dy * dy < 1.5:
                worker.state = "gathering"
                worker.destination = None
                self._gather_timers[worker.id] = 0.0
                event_bus.publish(GatheringStartedEvent(
                    worker_id=worker.id,
                    team=worker.team
                ))

        elif worker.state == "gathering":
            if worker.gather_target is None or worker.gather_target.depleted:
                # Mine depleted while gathering
                if worker.gather_target and worker.gather_target.depleted:
                    mine_pos = worker.gather_target.pos
                    worker.gather_target = None
                    worker.state = "idle"
                    event_bus.publish(MineDepletedEvent(
                        worker_id=worker.id,
                        team=worker.team,
                        mine_pos=mine_pos
                    ))
                else:
                    worker.state = "idle"
                return

            self._gather_timers[worker.id] = self._gather_timers.get(worker.id, 0) + dt

            if self._gather_timers[worker.id] >= self.GATHER_TIME:
                amount = min(self.GATHER_AMOUNT, worker.gather_target.minerals)
                worker.carrying = amount
                worker.gather_target.minerals -= amount
                worker.state = "returning"
                worker.destination = base.pos

        elif worker.state == "returning":
            dx = base.x - worker.x
            dy = base.y - worker.y
            if dx * dx + dy * dy < 2.0:
                # Deliver minerals
                self.world.team_minerals[worker.team] += worker.carrying

                event_bus.publish(ResourceCollectedEvent(
                    worker_id=worker.id,
                    team=worker.team,
                    amount=worker.carrying,
                    team_total=self.world.team_minerals[worker.team]
                ))

                worker.carrying = 0
                # Check if gather target is still valid
                if worker.gather_target and not worker.gather_target.depleted:
                    worker.state = "moving_to_mineral"
                    worker.destination = worker.gather_target.pos
                else:
                    # Mine depleted - wait for player command
                    if worker.gather_target and worker.gather_target.depleted:
                        mine_pos = worker.gather_target.pos
                        worker.gather_target = None
                        event_bus.publish(MineDepletedEvent(
                            worker_id=worker.id,
                            team=worker.team,
                            mine_pos=mine_pos
                        ))
                    worker.state = "idle"


class ProductionSystem:
    """Handles building production with queues."""

    def __init__(self, world):
        self.world = world
        self._waiting_for_minerals: Dict[int, float] = {}  # building_id -> cooldown for event

    def update(self, dt: float) -> None:
        """Process production for all buildings."""
        # Update waiting cooldowns
        for bid in list(self._waiting_for_minerals.keys()):
            self._waiting_for_minerals[bid] -= dt
            if self._waiting_for_minerals[bid] <= 0:
                del self._waiting_for_minerals[bid]

        for entity in list(self.world.entities.values()):
            if not isinstance(entity, Building) or not entity.alive:
                continue

            if not entity.production_queue:
                entity.waiting_for_minerals = False
                continue

            unit_type = entity.current_production
            build_time = entity.build_time
            cost = UNIT_STATS[unit_type]["cost"]

            # Check if we can afford (only check when starting)
            if entity.production_progress == 0:
                if self.world.team_minerals[entity.team] < cost:
                    entity.waiting_for_minerals = True
                    continue
                entity.waiting_for_minerals = False
                self.world.team_minerals[entity.team] -= cost

                event_bus.publish(ProductionStartedEvent(
                    building_id=entity.id,
                    unit_type=unit_type,
                    team=entity.team,
                    queue_position=len(entity.production_queue)
                ))
            else:
                entity.waiting_for_minerals = False

            # Progress production
            entity.production_progress += dt / build_time

            if entity.production_progress >= 1.0:
                # Complete production
                completed_type = entity.complete_production()

                # Spawn unit near building
                spawn_x = entity.x + random.uniform(-1, 1)
                spawn_y = entity.y + 2

                new_unit = self.world.spawn_entity(
                    completed_type,
                    entity.team,
                    (spawn_x, spawn_y)
                )

                event_bus.publish(ProductionCompletedEvent(
                    building_id=entity.id,
                    unit_type=completed_type,
                    unit_id=new_unit.id,
                    team=entity.team,
                    pos=new_unit.pos
                ))

                # Fire UnitReadyEvent with name/rank
                unit_name = random.choice(WORKER_NAMES)
                if completed_type == "Worker":
                    event_bus.publish(UnitReadyEvent(
                        unit_id=new_unit.id,
                        unit_type="Worker",
                        team=entity.team,
                        name=unit_name
                    ))
                elif completed_type == "Soldier":
                    unit_rank = random.choice(SOLDIER_RANKS)
                    event_bus.publish(UnitReadyEvent(
                        unit_id=new_unit.id,
                        unit_type="Soldier",
                        team=entity.team,
                        name=unit_name,
                        rank=unit_rank
                    ))

                # Set rally point if exists
                if entity.rally_point:
                    new_unit.destination = entity.rally_point

                # Auto-assign workers to gather minerals
                if isinstance(new_unit, Worker):
                    mineral = self.world.get_nearest_mineral(new_unit.x, new_unit.y)
                    if mineral:
                        new_unit.gather_target = mineral
                        new_unit.state = "moving_to_mineral"
                        new_unit.destination = mineral.pos


class BuildingPlacementSystem:
    """Handles worker building construction."""

    def __init__(self, world):
        self.world = world
        self._build_timers: Dict[int, float] = {}
        self._mineral_warning_cooldown: Dict[int, float] = {}  # Per-worker cooldown

    def update(self, dt: float) -> None:
        """Process building construction."""
        # Update cooldowns
        for wid in list(self._mineral_warning_cooldown.keys()):
            self._mineral_warning_cooldown[wid] -= dt
            if self._mineral_warning_cooldown[wid] <= 0:
                del self._mineral_warning_cooldown[wid]

        for entity in list(self.world.entities.values()):
            if not isinstance(entity, Worker) or not entity.alive:
                continue

            if entity.build_target is None:
                entity.waiting_for_minerals = False
                continue

            building_type, bx, by = entity.build_target

            # Validate build position is on the map and buildable
            if not self.world.game_map:
                entity.build_target = None
                entity.waiting_for_minerals = False
                continue

            bx_int, by_int = int(bx), int(by)
            if not (0 <= bx_int < self.world.game_map.width and 0 <= by_int < self.world.game_map.height):
                # Position is outside map - cancel build
                entity.build_target = None
                entity.waiting_for_minerals = False
                continue

            if not self.world.game_map.is_buildable(bx_int, by_int):
                # Position is not buildable - cancel build
                entity.build_target = None
                entity.waiting_for_minerals = False
                continue

            # Move to build site
            dx = bx - entity.x
            dy = by - entity.y
            dist = math.sqrt(dx * dx + dy * dy)

            if dist > 2.0:
                entity.destination = (bx, by)
                entity.waiting_for_minerals = False
                continue

            entity.destination = None

            # Check cost
            cost = BUILDING_STATS[building_type]["cost"]
            if self.world.team_minerals[entity.team] < cost:
                entity.waiting_for_minerals = True
                # Fire event if cooldown expired (for player only)
                if entity.team == 1 and entity.id not in self._mineral_warning_cooldown:
                    event_bus.publish(WorkerWaitingForMineralsEvent(
                        worker_id=entity.id,
                        team=entity.team,
                        building_type=building_type,
                        cost=cost
                    ))
                    self._mineral_warning_cooldown[entity.id] = 10.0  # 10 second cooldown
                continue

            entity.waiting_for_minerals = False

            # Fire construction start event (only once when timer starts)
            if entity.id not in self._build_timers:
                event_bus.publish(BuildingConstructionStartEvent(
                    worker_id=entity.id,
                    team=entity.team,
                    building_type=building_type,
                    pos=(bx, by)
                ))

            # Check for existing entities at build site
            occupied = False
            for other in self.world.entities.values():
                if other.alive and other.id != entity.id:
                    odx = other.x - bx
                    ody = other.y - by
                    if odx * odx + ody * ody < 2.0:
                        occupied = True
                        break
            if occupied:
                # Something is in the way - cancel build
                entity.build_target = None
                self._build_timers[entity.id] = 0
                continue

            # Progress building
            self._build_timers[entity.id] = self._build_timers.get(entity.id, 0) + dt
            build_time = BUILDING_STATS[building_type]["build_time"]

            if self._build_timers[entity.id] >= build_time:
                # Deduct cost
                self.world.team_minerals[entity.team] -= cost

                # Create building
                new_building = self.world.spawn_entity(building_type, entity.team, (bx, by))

                event_bus.publish(BuildingPlacedEvent(
                    building_id=new_building.id,
                    building_type=building_type,
                    team=entity.team,
                    pos=new_building.pos,
                    builder_id=entity.id
                ))

                entity.build_target = None
                self._build_timers[entity.id] = 0


class FogOfWarSystem:
    """Updates fog of war visibility."""

    def __init__(self, world):
        self.world = world

    def update(self, dt: float) -> None:
        """Update fog of war for all teams."""
        self.world.update_fog_of_war()


class AISystem:
    """Enhanced AI controller with scouting and raid behavior."""

    # AI States
    STATE_OPENING = "opening"           # Build initial workers
    STATE_ECONOMY = "economy"           # Build more workers, start gathering
    STATE_MILITARY_PREP = "military"    # Build barracks
    STATE_ARMY_BUILD = "army"           # Produce soldiers
    STATE_SCOUTING = "scouting"         # Soldiers explore the map
    STATE_RAID = "raid"                 # All-out attack on player base

    def __init__(self, world, team: int = 2, debug: bool = False):
        self.world = world
        self.team = team
        self.state = self.STATE_OPENING
        self.state_timer = 0.0
        self.debug = debug

        # Action cooldown (2 seconds between commands for realism)
        self.last_action_time = 0.0
        self.action_cooldown = 2.0

        # Thresholds
        self.min_workers = 4
        self.target_workers = 12        # Build about a dozen workers
        self.scout_army_size = 3        # Start scouting at 3 soldiers
        self.attack_army_size = 5       # Keep producing until 5

        # Scouting state
        self.scouting_waypoints = []
        self.player_base_found = False
        self.player_base_pos = None
        self.reinforcement_target = None
        self.spotted_enemies = set()    # Enemy IDs we've seen

    def _log(self, decision_type: str, message: str, details: dict = None) -> None:
        """Log an AI decision for debugging."""
        event_bus.publish(AIDecisionEvent(
            team=self.team,
            decision_type=decision_type,
            message=message,
            details=details
        ))

    def _can_take_action(self) -> bool:
        """Check if enough time has passed since last action."""
        return (self.state_timer - self.last_action_time) >= self.action_cooldown

    def _mark_action_taken(self) -> None:
        """Record that an action was taken."""
        self.last_action_time = self.state_timer

    def update(self, dt: float) -> None:
        """Run AI logic."""
        self.state_timer += dt

        # Get AI entities
        workers = [e for e in self.world.get_units(self.team) if isinstance(e, Worker)]
        soldiers = [e for e in self.world.get_units(self.team) if isinstance(e, Soldier)]
        base = self.world.get_base(self.team)
        barracks_list = [b for b in self.world.get_buildings(self.team) if isinstance(b, Barracks)]

        if not base or not base.alive:
            self._log("game_over", "AI base destroyed!")
            return

        # Log status every 10 seconds
        if int(self.state_timer) % 10 == 0 and int(self.state_timer) != int(self.state_timer - dt):
            self._log("status", f"State: {self.state} | Workers: {len(workers)} | Soldiers: {len(soldiers)} | Barracks: {len(barracks_list)} | Minerals: {self.world.team_minerals[self.team]}")

        # Check for enemies spotted by soldiers
        self._check_soldier_vision(soldiers)

        # State machine
        if self.state == self.STATE_OPENING:
            self._do_opening(base, workers)
        elif self.state == self.STATE_ECONOMY:
            self._do_economy(base, workers, barracks_list)
        elif self.state == self.STATE_MILITARY_PREP:
            self._do_military_prep(workers, barracks_list)
        elif self.state == self.STATE_ARMY_BUILD:
            self._do_army_build(barracks_list, soldiers)
        elif self.state == self.STATE_SCOUTING:
            self._do_scouting(soldiers, barracks_list)
        elif self.state == self.STATE_RAID:
            self._do_raid(soldiers)

        # Assign idle workers to gather
        self._assign_workers_to_gather(workers)

        # Check for idle/stuck soldiers every 16 seconds
        if int(self.state_timer) % 16 == 0 and int(self.state_timer) != int(self.state_timer - dt):
            self._reassign_idle_soldiers(soldiers)

    def _check_soldier_vision(self, soldiers: List[Soldier]) -> None:
        """Check what soldiers can see and react to enemies."""
        for soldier in soldiers:
            if not soldier.alive:
                continue

            # Find enemies in vision range
            enemies = self.world.get_enemies_in_range(soldier, soldier.vision)

            for enemy in enemies:
                if enemy.id in self.spotted_enemies:
                    continue

                self.spotted_enemies.add(enemy.id)
                self._log("enemy_spotted", f"Soldier {soldier.id} spotted {enemy.kind} at ({enemy.x:.1f}, {enemy.y:.1f})")

                # Check if it's the player base
                if isinstance(enemy, Base):
                    self.player_base_found = True
                    self.player_base_pos = enemy.pos
                    self._log("base_spotted", f"PLAYER BASE SPOTTED at {enemy.pos}!")
                    if self.state == self.STATE_SCOUTING:
                        self.state = self.STATE_RAID
                elif soldier.target is None:
                    # Attack this enemy and call for reinforcement
                    soldier.target = enemy.id
                    soldier.destination = enemy.pos
                    self.reinforcement_target = enemy.pos
                    self._log("engage", f"Soldier {soldier.id} engaging {enemy.kind} {enemy.id}")

    def _do_opening(self, base: Base, workers: List[Worker]) -> None:
        """Opening: Build workers until we have minimum."""
        if len(workers) >= self.min_workers:
            self._log("state_change", f"Opening complete, transitioning to ECONOMY (workers: {len(workers)}/{self.min_workers})")
            self.state = self.STATE_ECONOMY
            return

        if not base.production_queue and self.world.team_minerals[self.team] >= 50:
            if self._can_take_action():
                base.start_production()
                self._mark_action_taken()
                self._log("build_worker", f"Queued worker (workers: {len(workers)}, minerals: {self.world.team_minerals[self.team]})")

    def _do_economy(self, base: Base, workers: List[Worker], barracks_list: List[Barracks]) -> None:
        """Economy: Build workers and prepare for barracks."""
        # Build workers up to target
        if len(workers) < self.target_workers:
            if not base.production_queue and self.world.team_minerals[self.team] >= 50:
                if self._can_take_action():
                    base.start_production()
                    self._mark_action_taken()
                    self._log("build_worker", f"Queued worker in economy phase (workers: {len(workers)}/{self.target_workers})")

        # Transition to military when we have enough workers and minerals
        if len(workers) >= self.target_workers and self.world.team_minerals[self.team] >= 150:
            self._log("state_change", f"Economy complete, transitioning to MILITARY_PREP (workers: {len(workers)}, minerals: {self.world.team_minerals[self.team]})")
            self.state = self.STATE_MILITARY_PREP

    def _do_military_prep(self, workers: List[Worker], barracks_list: List[Barracks]) -> None:
        """Military Prep: Build barracks."""
        if barracks_list:
            self._log("state_change", f"Barracks built, transitioning to ARMY_BUILD")
            self.state = self.STATE_ARMY_BUILD
            return

        # Check if a worker is already building a barracks
        building_workers = [w for w in workers if w.build_target is not None]
        if building_workers:
            # Already have a worker building, just wait
            return

        # Check cooldown and minerals
        if not self._can_take_action():
            return
        if self.world.team_minerals[self.team] < 150:  # Barracks cost
            return

        # Find a worker to build barracks - take from gathering if needed
        candidate = None
        # First try workers not currently building
        for worker in workers:
            if worker.build_target is None:
                candidate = worker
                break

        if candidate:
            # Place barracks near base - try multiple random locations
            base = self.world.get_base(self.team)
            if base and self.world.game_map:
                build_pos = None
                for _ in range(20):  # Try up to 20 random positions
                    bx = base.x + random.uniform(-6, 6)
                    by = base.y + random.uniform(-6, 6)
                    # Snap to grid
                    bx, by = int(bx), int(by)
                    # Check if buildable
                    if self.world.game_map.is_buildable(bx, by):
                        # Check no entity at this position
                        occupied = False
                        for entity in self.world.entities.values():
                            if entity.alive:
                                dx = entity.x - bx
                                dy = entity.y - by
                                if dx * dx + dy * dy < 4.0:
                                    occupied = True
                                    break
                        if not occupied:
                            build_pos = (bx, by)
                            break

                if build_pos:
                    # Clear worker's current task
                    candidate.gather_target = None
                    candidate.state = "idle"
                    candidate.destination = None
                    candidate.build_target = ("Barracks", build_pos[0], build_pos[1])
                    self._mark_action_taken()
                    self._log("build_barracks", f"Assigned worker {candidate.id} to build Barracks at {build_pos}")
                else:
                    self._log("no_build_spot", "Military prep: No valid build location found near base")
        else:
            self._log("no_worker", "Military prep: No available worker to build barracks")

    def _do_army_build(self, barracks_list: List[Barracks], soldiers: List[Soldier]) -> None:
        """Army Build: Produce soldiers, transition to scouting at 3."""
        # Transition to scouting when we have enough soldiers
        if len(soldiers) >= self.scout_army_size:
            self._log("state_change", f"Army ready, transitioning to SCOUTING (soldiers: {len(soldiers)}/{self.scout_army_size})")
            self.state = self.STATE_SCOUTING
            return

        for barracks in barracks_list:
            if len(barracks.production_queue) < 3 and self.world.team_minerals[self.team] >= 75:
                if self._can_take_action():
                    barracks.start_production()
                    self._mark_action_taken()
                    self._log("build_soldier", f"Queued soldier (soldiers: {len(soldiers)}/{self.scout_army_size}, minerals: {self.world.team_minerals[self.team]})")
                    break  # Only queue one unit per action

    def _do_scouting(self, soldiers: List[Soldier], barracks_list: List[Barracks]) -> None:
        """Scouting: Send soldiers to explore, keep producing."""
        # Keep producing soldiers
        for barracks in barracks_list:
            if len(barracks.production_queue) < 2 and self.world.team_minerals[self.team] >= 75:
                if self._can_take_action():
                    barracks.start_production()
                    self._mark_action_taken()
                    self._log("build_soldier", f"Scouting: Queued additional soldier (total: {len(soldiers)})")
                    break  # Only queue one unit per action

        # Generate scouting waypoints if empty
        if not self.scouting_waypoints and self.world.game_map:
            width = self.world.game_map.width
            height = self.world.game_map.height
            # Generate random exploration points
            for _ in range(12):
                x = random.randint(5, width - 5)
                y = random.randint(5, height - 5)
                self.scouting_waypoints.append((x, y))
            self._log("scouting", f"Generated {len(self.scouting_waypoints)} scouting waypoints")

        # Handle reinforcement if enemies were spotted
        if self.reinforcement_target:
            idle_soldiers = [s for s in soldiers if s.target is None and s.destination is None]
            for soldier in idle_soldiers[:2]:  # Send up to 2 reinforcements
                soldier.destination = self.reinforcement_target
                self._log("reinforce", f"Sending soldier {soldier.id} to reinforce at {self.reinforcement_target}")
            # Clear after sending reinforcements
            self.reinforcement_target = None

        # Send idle soldiers to scout
        for soldier in soldiers:
            if soldier.destination is None and soldier.target is None:
                if self.scouting_waypoints:
                    waypoint = self.scouting_waypoints.pop(0)
                    soldier.destination = waypoint
                    # Put waypoint back at end for cycling
                    self.scouting_waypoints.append(waypoint)

        # Transition to raid if player base found
        if self.player_base_found:
            self._log("state_change", f"Player base found at {self.player_base_pos}, transitioning to RAID!")
            self.state = self.STATE_RAID

    def _do_raid(self, soldiers: List[Soldier]) -> None:
        """Raid: All-out attack on player base."""
        if not self.player_base_pos:
            # Try to find player base
            enemy_base = self.world.get_base(1)
            if enemy_base:
                self.player_base_pos = enemy_base.pos
                self._log("raid", f"Found player base at {self.player_base_pos}")
            else:
                self._log("raid", "Cannot find player base, aborting raid")
                return

        # Send ALL soldiers to player base
        for soldier in soldiers:
            if soldier.target is None or soldier.destination != self.player_base_pos:
                enemy_base = self.world.get_base(1)
                if enemy_base and enemy_base.alive:
                    was_new_target = soldier.target is None
                    soldier.target = enemy_base.id
                    soldier.destination = self.player_base_pos
                    if was_new_target:
                        self._log("attack", f"Soldier {soldier.id} attacking player base")

    def _assign_workers_to_gather(self, workers: List[Worker]) -> None:
        """Assign idle workers to gather minerals."""
        for worker in workers:
            if worker.state == "idle" and worker.gather_target is None:
                mineral = self.world.get_nearest_mineral(worker.x, worker.y)
                if mineral:
                    worker.gather_target = mineral
                    worker.state = "moving_to_mineral"
                    worker.destination = mineral.pos

    def _reassign_idle_soldiers(self, soldiers: List[Soldier]) -> None:
        """Reassign soldiers that have been idle/stuck for too long."""
        for soldier in soldiers:
            if not soldier.alive:
                continue

            # Check if soldier has an invalid target (dead or removed)
            if soldier.target is not None:
                target = self.world.get_entity(soldier.target)
                if target is None or not target.alive:
                    soldier.target = None
                    soldier.destination = None

            # Check if soldier is effectively idle (no target, no destination)
            is_idle = soldier.target is None and soldier.destination is None

            if is_idle:
                self._log("idle_soldier", f"Soldier {soldier.id} idle, reassigning")

                # Assign based on current AI state
                if self.state == self.STATE_RAID and self.player_base_pos:
                    # In raid mode, send to player base
                    soldier.destination = self.player_base_pos
                    enemy_base = self.world.get_base(1)
                    if enemy_base and enemy_base.alive:
                        soldier.target = enemy_base.id
                elif self.state == self.STATE_SCOUTING and self.scouting_waypoints:
                    # In scouting mode, send to a waypoint
                    waypoint = self.scouting_waypoints.pop(0)
                    soldier.destination = waypoint
                    self.scouting_waypoints.append(waypoint)
                else:
                    # Default: find nearest enemy
                    enemies = self.world.get_enemies_in_range(soldier, soldier.vision * 3)
                    if enemies:
                        nearest = min(enemies, key=lambda e: (e.x - soldier.x)**2 + (e.y - soldier.y)**2)
                        soldier.target = nearest.id
                        soldier.destination = nearest.pos
