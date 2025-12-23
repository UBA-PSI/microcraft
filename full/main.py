#!/usr/bin/env python3
"""
MicroCraft Full - Complete RTS Implementation
==============================================

Run with: python -m full.main [--verbose]

Features:
- A* Pathfinding
- Fog of War
- Production Queues (max 5)
- 5-state AI
- All event types
- Left-click only controls
"""
import argparse
import sys
import time
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from full.core.world import World
from full.core.systems import (
    MovementSystem,
    CombatSystem,
    ResourceSystem,
    ProductionSystem,
    BuildingPlacementSystem,
    FogOfWarSystem,
    AISystem,
)
from full.core.effects import ParticleSystem, ExplosionHandler, FestiveExplosionHandler, AttackFlashHandler, LoggerHandler, AILoggerHandler, GameMessageSystem, SFXEventHandler
from full.core.entities import Worker, Soldier, Building, Unit
from full.core.selection import SelectionManager, calculate_group_destinations
from full.core.events import event_bus, CommandEvent


DATA_DIR = PROJECT_ROOT / "data"


class Game:
    """Main game controller."""

    SIM_HZ = 30  # Simulation ticks per second
    SIM_DT = 1.0 / SIM_HZ
    CAMERA_SPEED = 15.0  # Tiles per second

    def __init__(self, verbose: bool = False, debug: bool = False, xmas: bool = False):
        self.world = World()
        self.particles = ParticleSystem()
        self.running = True
        self.verbose = verbose
        self.debug = debug
        self.xmas = xmas

        # Systems
        self.movement = MovementSystem(self.world)
        self.combat = CombatSystem(self.world)
        self.resources = ResourceSystem(self.world)
        self.production = ProductionSystem(self.world)
        self.building = BuildingPlacementSystem(self.world)
        self.fog = FogOfWarSystem(self.world)
        self.ai = AISystem(self.world, team=2, debug=debug)

        # Game messages (Funksprüche)
        self.messages = GameMessageSystem()

        # Effect handlers - festive explosions for Christmas mode
        if xmas:
            self.explosion_handler = FestiveExplosionHandler(self.particles)
        else:
            self.explosion_handler = ExplosionHandler(self.particles)
        self.attack_handler = AttackFlashHandler(self.particles, self.world)
        if verbose:
            self.logger = LoggerHandler(verbose=True)

        # AI Logger (always active in debug mode)
        if debug:
            self.ai_logger = AILoggerHandler(log_file="ai_debug.log")

        # Timing
        self.accumulator = 0.0
        self.last_time = time.time()

        # Selection & Build mode
        self.selection = SelectionManager()
        self.build_mode = False
        self.build_type = None

    def setup(self) -> None:
        """Initialize game state."""
        self.world.load_map(DATA_DIR / "map.csv")
        self.world.load_scenario(DATA_DIR / "scenario.json")

        # Assign workers to gather
        for entity in self.world.entities.values():
            if isinstance(entity, Worker):
                mineral = self.world.get_nearest_mineral(entity.x, entity.y)
                if mineral:
                    entity.gather_target = mineral
                    entity.state = "moving_to_mineral"
                    entity.destination = mineral.pos

    def update(self) -> None:
        """Update game state with fixed timestep."""
        current_time = time.time()
        frame_time = current_time - self.last_time
        self.last_time = current_time

        self.accumulator += frame_time

        while self.accumulator >= self.SIM_DT:
            self._tick(self.SIM_DT)
            self.accumulator -= self.SIM_DT

        # Update particles (can be variable rate)
        self.particles.update(frame_time)

        # Update game messages
        self.messages.update(frame_time)

    def _tick(self, dt: float) -> None:
        """Single simulation tick."""
        # Always update game_time (needed for game-over delay timer)
        self.world.game_time += dt

        # Pause simulation when game is over (but keep loop running for UI/explosions)
        if self.world.game_over:
            return

        self.movement.update(dt)
        self.combat.update(dt)
        self.resources.update(dt)
        self.production.update(dt)
        self.building.update(dt)
        self.fog.update(dt)
        self.ai.update(dt)

        self.world.check_victory()

    def handle_click(self, wx: float, wy: float) -> None:
        """Handle left-click at world position.

        Left-click behavior:
        - Click on own unit/building: Select it
        - Click on terrain (with units selected): Move there (group movement)
        - Click on enemy (with units selected): Attack
        - Click on mineral (with worker selected): Gather
        """
        clicked_entity = self.world.get_entity_at(wx, wy)

        # Get first selected entity for build mode / single unit commands
        first_selected = None
        if self.selection.selected_ids:
            first_id = next(iter(self.selection.selected_ids))
            first_selected = self.world.get_entity(first_id)

        # Build mode: place building
        if self.build_mode and self.build_type and first_selected:
            if isinstance(first_selected, Worker):
                first_selected.build_target = (self.build_type, wx, wy)
                self.build_mode = False
                self.build_type = None
                event_bus.publish(CommandEvent(entity_id=first_selected.id, team=1))
            return

        # Click on own entity: select it
        if clicked_entity and clicked_entity.team == 1:
            self.selection.select_single(clicked_entity.id)
            return

        # No selection: nothing to do
        if not self.selection.has_selection():
            return

        # Get all selected units (filter out dead and non-units)
        selected_units = []
        for eid in self.selection.selected_ids:
            entity = self.world.get_entity(eid)
            if entity and entity.alive and isinstance(entity, Unit):
                selected_units.append(entity)

        if not selected_units:
            return

        # Check for mineral click (only if single worker selected)
        # Use nearest mineral within 1.5 tiles so clicking near a mineral works
        if len(selected_units) == 1 and isinstance(selected_units[0], Worker):
            worker = selected_units[0]
            best_mineral = None
            best_dist_sq = 2.25  # 1.5^2
            for mineral in self.world.minerals.values():
                if not mineral.depleted:
                    dx = mineral.x - wx
                    dy = mineral.y - wy
                    dist_sq = dx * dx + dy * dy
                    if dist_sq < best_dist_sq:
                        best_dist_sq = dist_sq
                        best_mineral = mineral
            if best_mineral:
                worker.gather_target = best_mineral
                worker.state = "moving_to_mineral"
                worker.destination = best_mineral.pos
                worker.target = None
                event_bus.publish(CommandEvent(entity_id=worker.id, team=1))
                return

        # Click on enemy: attack (all selected units)
        if clicked_entity and clicked_entity.team != 1:
            for unit in selected_units:
                if isinstance(unit, Soldier):
                    unit.target = clicked_entity.id
                unit.destination = (clicked_entity.x, clicked_entity.y)
            # Publish command event for first unit
            if selected_units:
                event_bus.publish(CommandEvent(entity_id=selected_units[0].id, team=1))
            return

        # Click on terrain: group movement
        if len(selected_units) == 1:
            # Single unit: direct movement
            unit = selected_units[0]
            unit.destination = (wx, wy)
            unit.path = []
            unit.target = None
            if isinstance(unit, Worker):
                unit.gather_target = None
                unit.state = "idle"
            event_bus.publish(CommandEvent(entity_id=unit.id, team=1))
        else:
            # Multiple units: calculate group destinations
            destinations = calculate_group_destinations(
                selected_units, (wx, wy), self.world.game_map
            )
            for unit in selected_units:
                if unit.alive and unit.id in destinations:
                    unit.destination = destinations[unit.id]
                    unit.path = []
                    unit.target = None
                    if isinstance(unit, Worker):
                        unit.gather_target = None
                        unit.state = "idle"
            # Publish command event for first unit
            if selected_units:
                event_bus.publish(CommandEvent(entity_id=selected_units[0].id, team=1))

    def start_build_mode(self, building_type: str) -> None:
        """Enter build mode to place a building."""
        if not self.selection.selected_ids:
            return
        first_id = next(iter(self.selection.selected_ids))
        selected = self.world.get_entity(first_id)
        if isinstance(selected, Worker):
            self.build_mode = True
            self.build_type = building_type

    def request_production(self) -> None:
        """Request production from selected building."""
        from full.core.events import event_bus, InsufficientMineralsEvent
        from full.core.entities import UNIT_STATS, Base, Barracks

        if not self.selection.selected_ids:
            return

        first_id = next(iter(self.selection.selected_ids))
        entity = self.world.get_entity(first_id)
        if entity and hasattr(entity, 'start_production'):
            # Check mineral cost before queuing
            if isinstance(entity, Base):
                unit_type = "Worker"
            elif isinstance(entity, Barracks):
                unit_type = "Soldier"
            else:
                entity.start_production()
                return

            cost = UNIT_STATS[unit_type]["cost"]
            available = self.world.team_minerals[entity.team]

            # Fire event when we don't have enough minerals
            if available < cost:
                event_bus.publish(InsufficientMineralsEvent(
                    team=entity.team,
                    building_id=entity.id,
                    unit_type=unit_type,
                    cost=cost,
                    available=available
                ))

            entity.start_production()

    def cleanup(self) -> None:
        """Cleanup game resources."""
        pass

    def reset(self) -> None:
        """Reset game to initial state for a new game."""
        # Reinitialize world and particles
        self.world = World()
        self.particles = ParticleSystem()

        # Reinitialize all systems with new world
        self.movement = MovementSystem(self.world)
        self.combat = CombatSystem(self.world)
        self.resources = ResourceSystem(self.world)
        self.production = ProductionSystem(self.world)
        self.building = BuildingPlacementSystem(self.world)
        self.fog = FogOfWarSystem(self.world)
        self.ai = AISystem(self.world, team=2, debug=self.debug)

        # Reset game messages
        self.messages = GameMessageSystem()

        # Reinitialize effect handlers
        if self.xmas:
            self.explosion_handler = FestiveExplosionHandler(self.particles)
        else:
            self.explosion_handler = ExplosionHandler(self.particles)
        self.attack_handler = AttackFlashHandler(self.particles, self.world)
        if self.verbose:
            self.logger = LoggerHandler(verbose=True)

        # AI Logger (always active in debug mode)
        if self.debug:
            self.ai_logger = AILoggerHandler(log_file="ai_debug.log")

        # Reset timing
        self.accumulator = 0.0
        self.last_time = time.time()

        # Reset selection & build mode
        self.selection = SelectionManager()
        self.build_mode = False
        self.build_type = None

        # Reload scenario
        self.setup()


def main():
    parser = argparse.ArgumentParser(description="MicroCraft Full - Complete RTS")
    parser.add_argument('--verbose', action='store_true',
                       help='Print event log to console')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug mode (disable fog of war, log AI decisions)')
    parser.add_argument('--xmas', action='store_true',
                       help='Enable Christmas mode (festive explosions)')
    args = parser.parse_args()

    # Create game
    game = Game(verbose=args.verbose, debug=args.debug, xmas=args.xmas)

    # Create renderer (pygame only for full version)
    try:
        from frontends.pygame_renderer import PygameRenderer
        import pygame
        renderer = PygameRenderer(1024, 768)
    except ImportError as e:
        print(f"Error: pygame is required for full version: {e}")
        print("Install with: pip install pygame")
        sys.exit(1)

    # === Loading sequence ===
    # Musik läuft bereits, jetzt Map bauen
    renderer.show_loading_text("BUILDING MAP...")

    # Map laden (ohne Entities)
    game.world.load_map(DATA_DIR / "map.csv")
    renderer.prepare_terrain(game.world.game_map)

    renderer.show_loading_text("GETTING READY")
    renderer.sfx.play('getting_ready')
    pygame.time.wait(1000)

    # Szenario laden um Base-Position zu kennen (vor Fade-in)
    game.world.load_scenario(DATA_DIR / "scenario.json")

    # Kamera auf Spieler-Base setzen (kein Sprung nach Fade-in)
    player_base = game.world.get_base(1)
    if player_base:
        renderer.camera.center_on(player_base.x, player_base.y)
        renderer.camera.clamp_to_map(game.world.game_map.width, game.world.game_map.height)

    # Fade-in
    renderer.fade_in(1000, game.world.game_map)
    pygame.time.wait(1000)

    # Worker initialisieren
    for entity in game.world.entities.values():
        if isinstance(entity, Worker):
            mineral = game.world.get_nearest_mineral(entity.x, entity.y)
            if mineral:
                entity.gather_target = mineral
                entity.state = "moving_to_mineral"
                entity.destination = mineral.pos

    # Music event handler für Base-Angriffe
    from full.core.effects import MusicEventHandler
    music_handler = MusicEventHandler(renderer.music)

    # SFX event handler für Game-Events
    sfx_handler = SFXEventHandler(renderer.sfx)

    print("MicroCraft Full started!")
    print("Controls: WASD=Camera, Click=Select/Move/Attack, Q=Produce, B=Build, ESC=Quit")
    if args.verbose:
        print("Verbose mode: events will be logged")
    if args.debug:
        print("DEBUG MODE: Fog of war disabled, AI decisions logged to ai_debug.log")

    # Main game loop
    try:
        while game.running:
            input_state = renderer.handle_input()

            if input_state['quit']:
                game.running = False
                break

            # Game-Over Input Handling
            if game.world.game_over:
                # Play victory/defeat music and SFX (only once, MusicManager handles this via game_ended flag)
                if not renderer.music.game_ended:
                    if game.world.winner == 1:
                        renderer.sfx.play('victory')
                        renderer.music.play_victory()
                    else:
                        renderer.sfx.play('defeat')
                        renderer.music.play_defeat()

                    # Stop all loops
                    renderer.sfx.stop_all_loops()

                    # Stop all units (clear destinations)
                    for entity in game.world.entities.values():
                        if hasattr(entity, 'destination'):
                            entity.destination = None
                        if hasattr(entity, 'path'):
                            entity.path = []
                        if hasattr(entity, 'target'):
                            entity.target = None

                if input_state.get('key_r'):
                    # Reset game state (ohne setup aufzurufen)
                    game.world = World()
                    game.particles = ParticleSystem()
                    game.movement = MovementSystem(game.world)
                    game.combat = CombatSystem(game.world)
                    game.resources = ResourceSystem(game.world)
                    game.production = ProductionSystem(game.world)
                    game.building = BuildingPlacementSystem(game.world)
                    game.fog = FogOfWarSystem(game.world)
                    game.ai = AISystem(game.world, team=2, debug=game.debug)
                    game.messages = GameMessageSystem()
                    if game.xmas:
                        game.explosion_handler = FestiveExplosionHandler(game.particles)
                    else:
                        game.explosion_handler = ExplosionHandler(game.particles)
                    game.attack_handler = AttackFlashHandler(game.particles, game.world)
                    if game.verbose:
                        game.logger = LoggerHandler(verbose=True)
                    if game.debug:
                        game.ai_logger = AILoggerHandler(log_file="ai_debug.log")
                    game.accumulator = 0.0
                    game.last_time = time.time()
                    game.selection = SelectionManager()
                    game.build_mode = False
                    game.build_type = None

                    # Reset terrain surface
                    renderer._terrain_surface = None

                    # Loading sequence
                    renderer.music.reset()
                    renderer.show_loading_text("BUILDING MAP...")

                    game.world.load_map(DATA_DIR / "map.csv")
                    renderer.prepare_terrain(game.world.game_map)

                    renderer.show_loading_text("GETTING READY")
                    renderer.sfx.play('getting_ready')
                    pygame.time.wait(1000)

                    # Szenario laden um Base-Position zu kennen (vor Fade-in)
                    game.world.load_scenario(DATA_DIR / "scenario.json")

                    # Kamera auf Spieler-Base setzen (kein Sprung nach Fade-in)
                    player_base = game.world.get_base(1)
                    if player_base:
                        renderer.camera.center_on(player_base.x, player_base.y)
                        renderer.camera.clamp_to_map(game.world.game_map.width, game.world.game_map.height)

                    renderer.fade_in(1000, game.world.game_map)
                    pygame.time.wait(1000)

                    for entity in game.world.entities.values():
                        if isinstance(entity, Worker):
                            mineral = game.world.get_nearest_mineral(entity.x, entity.y)
                            if mineral:
                                entity.gather_target = mineral
                                entity.state = "moving_to_mineral"
                                entity.destination = mineral.pos

                    # Music and SFX event handlers neu erstellen
                    music_handler = MusicEventHandler(renderer.music)
                    sfx_handler = SFXEventHandler(renderer.sfx)
                    continue

                if input_state.get('key_q'):
                    game.running = False
                    break

                # Still render but skip game inputs
                game.update()
                renderer.render_frame(
                    game.world,
                    renderer.camera,
                    game.particles,
                    game.selection.selected_ids,
                    build_mode=game.build_mode,
                    build_type=game.build_type,
                    debug_mode=game.debug,
                    messages=game.messages.get_messages()
                )
                continue

            # Mouse down: start potential drag
            if input_state.get('mouse_down'):
                sx, sy = input_state['mouse_down']
                wx, wy = renderer.camera.screen_to_world(sx, sy)
                game.selection.start_drag(wx, wy)

            # Mouse held: update drag
            if input_state.get('mouse_held') and game.selection.drag_start:
                sx, sy = input_state['mouse_pos']
                wx, wy = renderer.camera.screen_to_world(sx, sy)
                game.selection.update_drag(wx, wy)

            # Mouse up: end drag or click
            if input_state.get('mouse_up'):
                sx, sy = input_state['mouse_up']
                wx, wy = renderer.camera.screen_to_world(sx, sy)

                if game.selection.is_dragging():
                    # Complete drag selection
                    selected = game.selection.end_drag(game.world, team=1)
                    if selected:
                        game.selection.selected_ids = selected
                else:
                    # Normal click
                    game.selection.cancel_drag()
                    game.handle_click(wx, wy)

            # Q: Production
            if input_state['key_q']:
                game.request_production()

            # B: Build mode (Barracks)
            if input_state.get('key_b'):
                game.start_build_mode("Barracks")

            # X: Debug explosion test (only in debug mode)
            if game.debug and input_state.get('key_x'):
                # Trigger base explosion at camera center
                from .core.events import event_bus, DeathEvent
                cx, cy = renderer.camera.x, renderer.camera.y  # Camera center in world coords
                event_bus.publish(DeathEvent(
                    entity_id=-1,
                    kind="Base",  # Triggers bombastic explosion
                    team=0,
                    pos=(cx, cy)
                ))

            # Camera movement (WASD/Arrow keys)
            dt = 1.0 / 60.0
            if input_state.get('camera_up'):
                renderer.camera.y -= game.CAMERA_SPEED * dt
            if input_state.get('camera_down'):
                renderer.camera.y += game.CAMERA_SPEED * dt
            if input_state.get('camera_left'):
                renderer.camera.x -= game.CAMERA_SPEED * dt
            if input_state.get('camera_right'):
                renderer.camera.x += game.CAMERA_SPEED * dt

            # Keep camera within map bounds
            if game.world.game_map:
                renderer.camera.clamp_to_map(
                    game.world.game_map.width,
                    game.world.game_map.height
                )

            game.update()
            sfx_handler.update(1.0 / 60.0)  # Update SFX timers

            # Movement loop sound for selected units
            any_moving = False
            for eid in game.selection.selected_ids:
                entity = game.world.get_entity(eid)
                if entity and entity.alive and hasattr(entity, 'destination'):
                    if entity.destination is not None:
                        any_moving = True
                        break
            if any_moving:
                renderer.sfx.play_loop('unit_moving')
            else:
                renderer.sfx.stop_loop('unit_moving')

            renderer.render_frame(
                game.world,
                renderer.camera,
                game.particles,
                game.selection.selected_ids,
                drag_rect=game.selection.get_drag_rect(),
                build_mode=game.build_mode,
                build_type=game.build_type,
                debug_mode=game.debug,
                messages=game.messages.get_messages()
            )

    except KeyboardInterrupt:
        pass
    finally:
        renderer.cleanup()
        game.cleanup()

    # Print result
    if game.world.game_over:
        if game.world.winner == 1:
            print("\n🎉 Victory! You defeated the AI!")
        else:
            print("\n💀 Defeat! The AI destroyed your base!")
    else:
        print("\nGame ended.")


if __name__ == '__main__':
    main()
