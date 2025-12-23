"""
Game Loop
Main game class that ties everything together.
"""
import time
from typing import Optional, Any
from .world import World
from .systems import MovementSystem, CombatSystem, ResourceSystem, ProductionSystem, AISystem, BuildingPlacementSystem
from .particle_system import ParticleSystem
from .config import TEAM_PLAYER, TEAM_AI, SIM_HZ, load_scenario


class Game:
    """Main game controller"""

    def __init__(self):
        self.world = World()
        self.particles = ParticleSystem()
        self.running = True
        self.paused = False

        # Selection state (for player input)
        self.selected_entity: Optional[int] = None

        # Build mode state
        self.build_mode = False
        self.build_type = None  # "Barracks" when in build mode

        # Initialize systems
        self.movement = MovementSystem()
        self.combat = CombatSystem()
        self.resources = ResourceSystem()
        self.production = ProductionSystem()
        self.building = BuildingPlacementSystem()
        self.ai = AISystem()

        # Timing
        self.last_time = time.time()
        self.sim_accumulator = 0.0
        self.sim_dt = 1.0 / SIM_HZ

    def setup(self) -> None:
        """Initialize game state - spawn starting entities"""
        from ..live.entities import Base, Worker
        from ..live.events import event_bus, SpawnEvent

        scenario = load_scenario()
        starting_workers = scenario.get("starting_workers", 3)

        # Spawn bases and workers for each team
        for team_id in [TEAM_PLAYER, TEAM_AI]:
            team_data = scenario["teams"].get(str(team_id), {})
            base_pos = team_data.get("base_pos", self.world.game_map.player_spawn if team_id == TEAM_PLAYER else self.world.game_map.ai_spawn)

            # Spawn base
            base_id = self.world.get_next_id()
            base = Base(base_id, team_id, tuple(base_pos))
            self.world.add_entity(base)

            event_bus.publish(SpawnEvent(
                kind="Base",
                entity_id=base_id,
                team=team_id,
                pos=tuple(base_pos)
            ))

            # Spawn starting workers
            for i in range(starting_workers):
                worker_id = self.world.get_next_id()
                wx = base_pos[0] + 1 + i
                wy = base_pos[1] + 1
                worker = Worker(worker_id, team_id, (wx, wy))
                self.world.add_entity(worker)

                event_bus.publish(SpawnEvent(
                    kind="Worker",
                    entity_id=worker_id,
                    team=team_id,
                    pos=(wx, wy)
                ))

    def update(self) -> None:
        """Update game state (called every frame)"""
        current_time = time.time()
        frame_dt = current_time - self.last_time
        self.last_time = current_time

        if self.paused:
            return

        # Accumulate time for fixed timestep simulation
        self.sim_accumulator += frame_dt

        while self.sim_accumulator >= self.sim_dt:
            self._sim_step(self.sim_dt)
            self.sim_accumulator -= self.sim_dt

        # Update particles (can run at frame rate)
        self.particles.update(frame_dt)

    def _sim_step(self, dt: float) -> None:
        """One simulation step at fixed timestep"""
        self.world.game_time += dt

        # Update all systems
        self.movement.update(self.world, dt)
        self.combat.update(self.world, dt)
        self.resources.update(self.world, dt)
        self.production.update(self.world, dt)
        self.building.update(self.world, dt)
        self.ai.update(self.world, dt)

        # Check victory
        self.world.check_victory()
        if self.world.game_over:
            self.running = False

    def select_at(self, x: float, y: float) -> Optional[int]:
        """Select entity at world position"""
        # Find entity near click position
        best = None
        best_dist = 1.5  # Selection radius

        for entity in self.world.entities.values():
            if entity.team != TEAM_PLAYER:
                continue
            dx = entity.x - x
            dy = entity.y - y
            dist = (dx * dx + dy * dy) ** 0.5
            if dist < best_dist:
                best_dist = dist
                best = entity.id

        self.selected_entity = best
        return best

    def issue_command(self, target_x: float, target_y: float) -> None:
        """Issue move/attack command to selected unit"""
        from ..live.entities import Unit, Worker, Soldier
        from ..live.events import event_bus, CommandEvent

        if self.selected_entity is None:
            return

        entity = self.world.get_entity(self.selected_entity)
        if entity is None or not isinstance(entity, Unit):
            return

        # Handle build mode
        if self.build_mode and self.build_type and isinstance(entity, Worker):
            entity.build_target = (self.build_type, target_x, target_y)
            entity.destination = (target_x, target_y)  # Start moving to build site
            entity.gather_target = None  # Stop gathering
            self.build_mode = False
            self.build_type = None
            # Publish command event
            event_bus.publish(CommandEvent(entity_id=entity.id, team=entity.team))
            return

        # Check if clicking on mineral (for workers)
        # Use nearest mineral within 1.5 tiles so clicking near a mineral works
        if isinstance(entity, Worker):
            mineral = self.world.game_map.get_nearest_mineral(target_x, target_y)
            if mineral:
                # Check if click was close enough to the mineral (within 1.5 tiles)
                dx = mineral.x - target_x
                dy = mineral.y - target_y
                if dx * dx + dy * dy <= 2.25:  # 1.5^2
                    entity.gather_target = mineral
                    entity.destination = (mineral.x, mineral.y)
                    # Publish command event
                    event_bus.publish(CommandEvent(entity_id=entity.id, team=entity.team))
                    return

        # Check if clicking on enemy (for attack)
        for other in self.world.entities.values():
            if other.team != entity.team and other.alive:
                dx = other.x - target_x
                dy = other.y - target_y
                if abs(dx) < 1 and abs(dy) < 1:
                    # Clicked on enemy
                    if isinstance(entity, Soldier):
                        entity.target = other.id
                    entity.destination = (other.x, other.y)
                    # Publish command event
                    event_bus.publish(CommandEvent(entity_id=entity.id, team=entity.team))
                    return

        # Default: move command
        entity.destination = (target_x, target_y)
        # Publish command event
        event_bus.publish(CommandEvent(entity_id=entity.id, team=entity.team))

    def start_build_mode(self) -> None:
        """Enter build mode for Barracks placement"""
        from ..live.entities import Worker

        if self.selected_entity is None:
            return

        entity = self.world.get_entity(self.selected_entity)
        if entity and isinstance(entity, Worker) and entity.team == TEAM_PLAYER:
            self.build_mode = True
            self.build_type = "Barracks"

    def request_production(self) -> bool:
        """Request selected building to produce a unit"""
        from ..live.entities import Building, Base, Barracks

        if self.selected_entity is None:
            return False

        entity = self.world.get_entity(self.selected_entity)
        if entity is None or not isinstance(entity, Building):
            return False

        if entity.team != TEAM_PLAYER:
            return False

        if entity.current_production is not None:
            return False  # Already producing

        # Determine what to produce
        if isinstance(entity, Base):
            unit_type = "Worker"
        elif isinstance(entity, Barracks):
            unit_type = "Soldier"
        else:
            return False

        # Check cost
        from .config import UNIT_STATS
        cost = UNIT_STATS[unit_type]["cost"]
        current = self.world.get_minerals(TEAM_PLAYER)
        if current < cost:
            print(f"Not enough minerals! Need {cost}, have {current}")
            return False
        if not self.world.spend_minerals(TEAM_PLAYER, cost):
            return False  # Not enough minerals

        # Start production
        entity.start_production()
        return True

    def cleanup(self) -> None:
        """Clean up resources"""
        self.particles.clear()
