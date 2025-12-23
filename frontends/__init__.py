"""
MicroCraft Frontends
Renderers for different display modes.

DUCK TYPING EXAMPLE:
Both renderers have the same interface:
- __init__(width, height)
- render_frame(world, camera, particles, selected_id)
- handle_input() -> dict
- cleanup()

No shared base class needed! Just swap them:

    # Simple shapes (circles/rectangles)
    renderer = SimpleRenderer(1024, 768)

    # Or with sprites
    renderer = SpriteRenderer(1024, 768)

    # Game loop works with either:
    while running:
        renderer.render_frame(world, camera, particles)
"""

# Note: Don't import renderers here to avoid importing pygame
# when it might not be needed. Import directly in main.py instead.
