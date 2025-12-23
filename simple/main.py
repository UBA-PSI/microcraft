#!/usr/bin/env python3
"""
MicroCraft Simple - Main Entry Point
=====================================

This is the lecture live-coding version.
Run with: python -m simple.main [--console]

For the lecture:
1. Start with simple/live/ files empty
2. Live-code entities.py, events.py, effects_festive.py
3. Watch the game come to life!

For testing/demo:
- Copy files from simple/ref/ to simple/live/
- Or use --use-ref flag to load reference implementations directly
"""
import argparse
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    parser = argparse.ArgumentParser(description="MicroCraft - StarCraft-style RTS for teaching OOP")
    parser.add_argument('--use-ref', action='store_true',
                       help='Use reference implementations from simple/ref/')
    parser.add_argument('--simple-renderer', action='store_true',
                       help='Use simple shapes renderer (ignored - always used in simple mode)')
    args = parser.parse_args()

    # Choose which entity/event implementations to use
    if args.use_ref:
        print("Using reference implementations from simple/ref/")
        # Monkey-patch the live module to use ref implementations
        from simple import ref
        from simple import live
        live.entities = ref.entities
        live.events = ref.events
        live.effects_festive = ref.effects_festive
        live.audio = ref.audio

        # Also update sys.modules so imports work
        sys.modules['simple.live.entities'] = ref.entities
        sys.modules['simple.live.events'] = ref.events
        sys.modules['simple.live.effects_festive'] = ref.effects_festive
        sys.modules['simple.live.audio'] = ref.audio

    # Import game components (after potential monkey-patching)
    try:
        from simple.shared.game import Game
        from simple.live.events import event_bus
    except ImportError as e:
        print(f"Error: Could not import live-coded modules: {e}")
        print("\nHave you implemented the files in simple/live/?")
        print("Or use --use-ref to use reference implementations.")
        sys.exit(1)

    # FestiveExplosionHandler is optional - game works without it
    try:
        from simple.live.effects_festive import FestiveExplosionHandler
    except ImportError:
        FestiveExplosionHandler = None

    # Create game
    game = Game()

    # Create renderer - simple mode always uses SimpleRenderer
    # (PygameRenderer requires full mode code that isn't available here)
    from frontends.simple_renderer import SimpleRenderer
    renderer = SimpleRenderer(1024, 768)

    # Initialize game
    game.setup()

    # Register the festive explosion handler (IoC demo!)
    # Optional: Only if effects_festive.py has been implemented
    festive_handler = None
    if FestiveExplosionHandler:
        festive_handler = FestiveExplosionHandler(game.particles)

    # Register sound handler
    sound_handler = None
    if True:  # Always try to load audio in pygame mode
        try:
            from simple.live.audio import SoundHandler
            sounds_dir = PROJECT_ROOT / "assets" / "sounds"
            sound_handler = SoundHandler(sounds_dir, enabled=True)
        except ImportError:
            pass  # Audio module not available

    # Center camera on player base
    player_base = game.world.get_base(1)
    if player_base:
        renderer.camera.center_on(player_base.x, player_base.y)

    print("MicroCraft started!")
    print("Controls: WASD/Arrows move camera, LMB select/command, Q produce, B build, ESC quit")

    # Main game loop
    try:
        while game.running:
            # Handle input
            input_state = renderer.handle_input()

            if input_state['quit']:
                # ESC cancels build mode first, then quits
                if game.build_mode:
                    game.build_mode = False
                    game.build_type = None
                else:
                    game.running = False
                    break

            # Handle left-click (smart click: select own / command selected)
            if input_state['left_click']:
                sx, sy = input_state['left_click']
                wx, wy = renderer.camera.screen_to_world(sx, sy)

                # Check what was clicked
                clicked_entity = None
                best_dist = 1.5  # Selection radius
                for entity in game.world.entities.values():
                    dx = entity.x - wx
                    dy = entity.y - wy
                    dist = (dx * dx + dy * dy) ** 0.5
                    if dist < best_dist:
                        best_dist = dist
                        clicked_entity = entity

                # Determine action: select own entity or command selected unit
                if clicked_entity and clicked_entity.team == 1:
                    # Click on own entity: select it
                    game.select_at(wx, wy)
                elif game.selected_entity is not None:
                    # Has selection and clicked elsewhere: issue command
                    game.issue_command(wx, wy)
                else:
                    # No entity clicked, no selection: deselect
                    game.selected_entity = None

            # Handle production (Q key)
            if input_state['key_q']:
                game.request_production()

            # Handle building (B key)
            if input_state.get('key_b'):
                game.start_build_mode()

            # Camera movement (WASD/Arrow keys)
            camera_speed = 15.0  # Tiles per second
            dt = 1.0 / 60.0  # Approximate frame time
            if input_state.get('camera_up'):
                renderer.camera.y -= camera_speed * dt
            if input_state.get('camera_down'):
                renderer.camera.y += camera_speed * dt
            if input_state.get('camera_left'):
                renderer.camera.x -= camera_speed * dt
            if input_state.get('camera_right'):
                renderer.camera.x += camera_speed * dt

            # Update game state
            game.update()

            # Render
            renderer.render_frame(
                game.world,
                renderer.camera,
                game.particles,
                game.selected_entity,
                build_mode=game.build_mode
            )

    except KeyboardInterrupt:
        pass
    finally:
        renderer.cleanup()
        game.cleanup()
        if sound_handler:
            sound_handler.cleanup()

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
