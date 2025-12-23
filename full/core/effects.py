"""
MicroCraft Full Effects - Particle and Visual Effects

Handles all visual effects including:
- Death explosions (festive and regular)
- Attack flashes
- Resource collection sparkles
"""
import random
import math
from dataclasses import dataclass
from typing import List, Optional

import random as _random
from .events import (
    event_bus, DeathEvent, AttackEvent, ResourceCollectedEvent,
    MineDepletedEvent, BaseUnderAttackEvent, AIDecisionEvent,
    InsufficientMineralsEvent, WorkerWaitingForMineralsEvent, UnitReadyEvent,
    ProductionCompletedEvent, ProductionStartedEvent, GatheringStartedEvent,
    BuildingConstructionStartEvent, BuildingPlacedEvent, CommandEvent
)

# Worker names (short English first names)
WORKER_NAMES = [
    "Max", "Tom", "Ben", "Sam", "Joe", "Dan", "Jim", "Bob", "Tim", "Leo",
    "Jack", "Mike", "Nick", "Paul", "Rick", "Zack", "Finn", "Cole", "Luke", "Ryan",
    "Emma", "Anna", "Lisa", "Sara", "Kate", "Jane", "Amy", "Meg", "Eve", "Lily"
]

# Soldier ranks (German military)
SOLDIER_RANKS = [
    "Gefreiter", "Obergefreiter", "Hauptgefreiter", "Stabsgefreiter",
    "Unteroffizier", "Stabsunteroffizier", "Feldwebel", "Oberfeldwebel"
]

# Soldier ready phrases
SOLDIER_PHRASES = [
    "Zu Diensten!",
    "Bereit!",
    "Einsatzbereit!",
    "Auf Position!",
    "Melde mich zum Dienst!"
]


@dataclass
class Particle:
    """A single particle in the system."""
    x: float
    y: float
    vx: float
    vy: float
    color: str
    lifetime: float
    max_lifetime: float
    size: float

    @property
    def alive(self) -> bool:
        return self.lifetime > 0

    @property
    def alpha(self) -> float:
        """Fade out as lifetime decreases."""
        return max(0, min(1, self.lifetime / self.max_lifetime))


@dataclass
class LaserBeam:
    """A laser beam effect from attacker to target."""
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    lifetime: float
    max_lifetime: float
    color: str = "#FF4444"  # Red laser

    @property
    def alive(self) -> bool:
        return self.lifetime > 0

    @property
    def alpha(self) -> float:
        """Fade out as lifetime decreases."""
        return max(0, min(1, self.lifetime / self.max_lifetime))


@dataclass
class ExplosionFlash:
    """An expanding circle flash effect at destruction point."""
    x: float
    y: float
    current_radius: float
    max_radius: float
    lifetime: float
    max_lifetime: float
    color: str = "#FFFFFF"  # White flash

    @property
    def alive(self) -> bool:
        return self.lifetime > 0

    @property
    def alpha(self) -> float:
        """Fade out as lifetime decreases."""
        return max(0, min(1, self.lifetime / self.max_lifetime))

    @property
    def progress(self) -> float:
        """Expansion progress 0.0 to 1.0."""
        return 1.0 - (self.lifetime / self.max_lifetime)


class ParticleSystem:
    """Manages particle effects, laser beams, and explosion flashes."""

    def __init__(self, max_particles: int = 3000):
        self.particles: List[Particle] = []
        self.laser_beams: List[LaserBeam] = []
        self.explosion_flashes: List[ExplosionFlash] = []
        self.hit_flash_entities: dict = {}  # entity_id -> remaining_time
        self.max_particles = max_particles

    def update(self, dt: float) -> None:
        """Update all effects."""
        # Update particles
        for particle in self.particles:
            particle.x += particle.vx * dt
            particle.y += particle.vy * dt
            particle.lifetime -= dt
            particle.vy += 50 * dt  # Gravity

        # Update laser beams
        for beam in self.laser_beams:
            beam.lifetime -= dt

        # Update explosion flashes
        for flash in self.explosion_flashes:
            flash.lifetime -= dt
            # Expand radius based on progress
            flash.current_radius = flash.max_radius * flash.progress

        # Update hit flashes
        for entity_id in list(self.hit_flash_entities.keys()):
            self.hit_flash_entities[entity_id] -= dt
            if self.hit_flash_entities[entity_id] <= 0:
                del self.hit_flash_entities[entity_id]

        # Remove dead effects
        self.particles = [p for p in self.particles if p.alive]
        self.laser_beams = [b for b in self.laser_beams if b.alive]
        self.explosion_flashes = [f for f in self.explosion_flashes if f.alive]

    def get_particles(self) -> List[Particle]:
        """Get all active particles for rendering."""
        return self.particles

    def get_laser_beams(self) -> List[LaserBeam]:
        """Get all active laser beams for rendering."""
        return self.laser_beams

    def get_explosion_flashes(self) -> List[ExplosionFlash]:
        """Get all active explosion flashes for rendering."""
        return self.explosion_flashes

    def is_entity_hit_flashing(self, entity_id: int) -> bool:
        """Check if entity should be rendered with hit flash."""
        return entity_id in self.hit_flash_entities

    def clear(self) -> None:
        """Remove all effects."""
        self.particles.clear()
        self.laser_beams.clear()
        self.explosion_flashes.clear()
        self.hit_flash_entities.clear()

    def spawn(
        self,
        x: float,
        y: float,
        angle: float,
        speed: float,
        color: str,
        lifetime: float,
        size: float = 3
    ) -> None:
        """Spawn a single particle."""
        if len(self.particles) >= self.max_particles:
            return

        rad = math.radians(angle)
        particle = Particle(
            x=x,
            y=y,
            vx=math.cos(rad) * speed,
            vy=math.sin(rad) * speed,
            color=color,
            lifetime=lifetime,
            max_lifetime=lifetime,
            size=size
        )
        self.particles.append(particle)

    def spawn_burst(
        self,
        x: float,
        y: float,
        count: int,
        min_speed: float,
        max_speed: float,
        colors: List[str],
        min_lifetime: float = 0.5,
        max_lifetime: float = 1.5,
        min_size: float = 2,
        max_size: float = 5
    ) -> None:
        """Spawn a burst of particles in all directions."""
        for _ in range(count):
            angle = random.uniform(0, 360)
            speed = random.uniform(min_speed, max_speed)
            color = random.choice(colors)
            lifetime = random.uniform(min_lifetime, max_lifetime)
            size = random.uniform(min_size, max_size)
            self.spawn(x, y, angle, speed, color, lifetime, size)

    def spawn_laser_beam(
        self,
        start_x: float,
        start_y: float,
        end_x: float,
        end_y: float,
        lifetime: float = 0.15,
        color: str = "#FF4444"
    ) -> None:
        """Spawn a laser beam from start to end position."""
        beam = LaserBeam(
            start_x=start_x,
            start_y=start_y,
            end_x=end_x,
            end_y=end_y,
            lifetime=lifetime,
            max_lifetime=lifetime,
            color=color
        )
        self.laser_beams.append(beam)

    def spawn_explosion_flash(
        self,
        x: float,
        y: float,
        max_radius: float = 2.0,
        lifetime: float = 0.3,
        color: str = "#FFFFFF"
    ) -> None:
        """Spawn an expanding explosion flash at position."""
        flash = ExplosionFlash(
            x=x,
            y=y,
            current_radius=0.0,
            max_radius=max_radius,
            lifetime=lifetime,
            max_lifetime=lifetime,
            color=color
        )
        self.explosion_flashes.append(flash)

    def spawn_hit_flash(self, entity_id: int, duration: float = 0.2) -> None:
        """Mark an entity to flash white when hit."""
        self.hit_flash_entities[entity_id] = duration


class ExplosionHandler:
    """Subscribes to DeathEvent, spawns normal explosions (not festive)."""

    # Normal explosion colors (fire and smoke)
    EXPLOSION_COLORS = [
        "#FF4500",  # Orange-Red
        "#FF6600",  # Orange
        "#FFCC00",  # Yellow
        "#FF3300",  # Red-Orange
    ]

    SMOKE_COLORS = [
        "#444444",  # Dark gray
        "#666666",  # Medium gray
        "#888888",  # Light gray
    ]

    def __init__(self, particle_system: ParticleSystem):
        self.particles = particle_system
        event_bus.subscribe(DeathEvent, self.on_death)

    def on_death(self, event: DeathEvent) -> None:
        """Handle a death event with normal explosion."""
        x, y = event.pos
        is_base = event.kind == "Base"

        if is_base:
            # Big base explosion
            self.particles.spawn_explosion_flash(
                x=x, y=y, max_radius=35.0, lifetime=0.5, color="#FF6600"
            )
            self.particles.spawn_explosion_flash(
                x=x, y=y, max_radius=25.0, lifetime=0.4, color="#FFCC00"
            )

            # Fire particles
            for _ in range(4):
                self.particles.spawn_burst(
                    x=x, y=y,
                    count=40,
                    min_speed=60, max_speed=300,
                    colors=self.EXPLOSION_COLORS,
                    min_lifetime=1.0, max_lifetime=2.5,
                    min_size=3, max_size=10
                )

            # Smoke
            for _ in range(30):
                self.particles.spawn(
                    x=x + random.uniform(-0.5, 0.5),
                    y=y + random.uniform(-0.5, 0.5),
                    angle=random.uniform(60, 120),  # Upward
                    speed=random.uniform(30, 80),
                    color=random.choice(self.SMOKE_COLORS),
                    lifetime=random.uniform(1.5, 3.0),
                    size=random.uniform(4, 8)
                )
        else:
            # Unit explosion
            self.particles.spawn_explosion_flash(
                x=x, y=y, max_radius=8.0, lifetime=0.2, color="#FF6600"
            )

            self.particles.spawn_burst(
                x=x, y=y,
                count=15,
                min_speed=40, max_speed=150,
                colors=self.EXPLOSION_COLORS,
                min_lifetime=0.4, max_lifetime=1.0,
                min_size=2, max_size=5
            )

            # Small smoke puff
            for _ in range(5):
                self.particles.spawn(
                    x=x + random.uniform(-0.2, 0.2),
                    y=y + random.uniform(-0.2, 0.2),
                    angle=random.uniform(60, 120),
                    speed=random.uniform(20, 50),
                    color=random.choice(self.SMOKE_COLORS),
                    lifetime=random.uniform(0.5, 1.0),
                    size=random.uniform(2, 4)
                )


class FestiveExplosionHandler:
    """Subscribes to DeathEvent, spawns festive Christmas explosions."""

    # Festive Christmas colors
    CHRISTMAS_COLORS = [
        "#FF0000",  # Red
        "#00FF00",  # Green
        "#FFFFFF",  # White
        "#FFD700",  # Gold
    ]

    # Confetti colors (more variety)
    CONFETTI_COLORS = [
        "#FF0000",  # Red
        "#00FF00",  # Green
        "#FFFFFF",  # White
        "#FFD700",  # Gold
        "#FF69B4",  # Pink
        "#00CED1",  # Cyan
        "#FF4500",  # Orange-Red
        "#98FB98",  # Pale Green
    ]

    def __init__(self, particle_system: ParticleSystem):
        self.particles = particle_system
        event_bus.subscribe(DeathEvent, self.on_death)

    def on_death(self, event: DeathEvent) -> None:
        """Handle a death event with festive Christmas explosion."""
        x, y = event.pos
        is_base = event.kind == "Base"

        if is_base:
            # === ULTRA DRAMATIC FESTIVE BASE EXPLOSION ===
            # Multiple expanding rings: White -> Red -> Green (staggered)
            self.particles.spawn_explosion_flash(
                x=x, y=y, max_radius=40.0, lifetime=0.6, color="#FFFFFF"
            )
            self.particles.spawn_explosion_flash(
                x=x, y=y, max_radius=35.0, lifetime=0.5, color="#FF0000"
            )
            self.particles.spawn_explosion_flash(
                x=x, y=y, max_radius=30.0, lifetime=0.4, color="#00FF00"
            )
            self.particles.spawn_explosion_flash(
                x=x, y=y, max_radius=25.0, lifetime=0.35, color="#FFD700"
            )

            # MASSIVE particle bursts in Christmas colors
            for burst in range(6):
                self.particles.spawn_burst(
                    x=x,
                    y=y,
                    count=70,
                    min_speed=80,
                    max_speed=500,
                    colors=self.CHRISTMAS_COLORS,
                    min_lifetime=2.0,
                    max_lifetime=5.0,
                    min_size=4,
                    max_size=15
                )

            # Tons of sparkles flying outward (long-lasting)
            for _ in range(80):
                self.particles.spawn(
                    x=x + random.uniform(-1.0, 1.0),
                    y=y + random.uniform(-1.0, 1.0),
                    angle=random.uniform(0, 360),
                    speed=random.uniform(100, 450),
                    color="#FFFFFF",
                    lifetime=random.uniform(2.0, 4.0),
                    size=random.uniform(1, 3)
                )

            # Festive colored debris (bigger, longer)
            for _ in range(60):
                self.particles.spawn(
                    x=x + random.uniform(-2.0, 2.0),
                    y=y + random.uniform(-2.0, 2.0),
                    angle=random.uniform(0, 360),
                    speed=random.uniform(150, 550),
                    color=random.choice(self.CHRISTMAS_COLORS),
                    lifetime=random.uniform(2.5, 5.0),
                    size=random.randint(6, 18)
                )

            # === CONFETTI SNOWFLAKE RAIN ===
            # Spawn LOTS of confetti across entire screen area
            for _ in range(300):
                # Random position across very wide area (whole screen)
                confetti_x = x + random.uniform(-40, 40)
                confetti_y = y + random.uniform(-30, -3)  # Start above
                # Mostly downward with slight sideways drift
                angle = random.uniform(75, 105)  # Roughly downward
                self.particles.spawn(
                    x=confetti_x,
                    y=confetti_y,
                    angle=angle,
                    speed=random.uniform(15, 60),
                    color=random.choice(self.CONFETTI_COLORS),
                    lifetime=random.uniform(5.0, 10.0),
                    size=random.uniform(3, 7)
                )

            # MASSIVE white snowflakes (bigger, very visible)
            for _ in range(250):
                confetti_x = x + random.uniform(-45, 45)
                confetti_y = y + random.uniform(-35, -5)
                self.particles.spawn(
                    x=confetti_x,
                    y=confetti_y,
                    angle=random.uniform(85, 95),  # Almost straight down
                    speed=random.uniform(8, 35),
                    color="#FFFFFF",
                    lifetime=random.uniform(6.0, 12.0),
                    size=random.uniform(3, 6)
                )

            # Extra gold/silver glitter
            for _ in range(100):
                confetti_x = x + random.uniform(-35, 35)
                confetti_y = y + random.uniform(-25, -2)
                self.particles.spawn(
                    x=confetti_x,
                    y=confetti_y,
                    angle=random.uniform(80, 100),
                    speed=random.uniform(20, 70),
                    color=random.choice(["#FFD700", "#C0C0C0", "#FFFACD"]),
                    lifetime=random.uniform(5.0, 9.0),
                    size=random.uniform(2, 4)
                )

        else:
            # === FESTIVE UNIT EXPLOSION (2+ sec) ===
            # Double flash (white + colored)
            self.particles.spawn_explosion_flash(
                x=x, y=y, max_radius=3.5, lifetime=0.35, color="#FFFFFF"
            )
            self.particles.spawn_explosion_flash(
                x=x, y=y, max_radius=2.5, lifetime=0.25, color=random.choice(["#FF0000", "#00FF00"])
            )

            # Bigger Christmas colored particle burst
            self.particles.spawn_burst(
                x=x,
                y=y,
                count=25,
                min_speed=50,
                max_speed=200,
                colors=self.CHRISTMAS_COLORS,
                min_lifetime=1.2,
                max_lifetime=2.5,
                min_size=3,
                max_size=8
            )

            # Lots of sparkles (longer lifetime)
            for _ in range(25):
                self.particles.spawn(
                    x=x + random.uniform(-0.4, 0.4),
                    y=y + random.uniform(-0.4, 0.4),
                    angle=random.uniform(0, 360),
                    speed=random.uniform(60, 180),
                    color="#FFFFFF",
                    lifetime=random.uniform(1.5, 2.5),
                    size=random.uniform(1, 2)
                )

            # Mini confetti burst
            for _ in range(15):
                self.particles.spawn(
                    x=x + random.uniform(-0.5, 0.5),
                    y=y + random.uniform(-2, -0.5),
                    angle=random.uniform(70, 110),
                    speed=random.uniform(15, 50),
                    color=random.choice(self.CONFETTI_COLORS),
                    lifetime=random.uniform(2.0, 3.5),
                    size=random.uniform(2, 4)
                )


class AttackFlashHandler:
    """Shows laser beam and hit flash effects when units attack."""

    def __init__(self, particle_system: ParticleSystem, world=None):
        self.particles = particle_system
        self.world = world
        event_bus.subscribe(AttackEvent, self.on_attack)

    def set_world(self, world) -> None:
        """Set world reference (needed to get entity positions)."""
        self.world = world

    def on_attack(self, event: AttackEvent) -> None:
        """Show laser beam from attacker to target, and hit flash on target."""
        if not self.world:
            return

        attacker = self.world.get_entity(event.attacker_id)
        target = self.world.get_entity(event.target_id)

        if not attacker or not target:
            return

        # Spawn laser beam from attacker to target
        # Use team color for laser
        if attacker.team == 1:
            laser_color = "#4499FF"  # Blue for player
        else:
            laser_color = "#FF4444"  # Red for AI

        self.particles.spawn_laser_beam(
            start_x=attacker.x,
            start_y=attacker.y,
            end_x=target.x,
            end_y=target.y,
            lifetime=0.15,
            color=laser_color
        )

        # Spawn hit flash on target
        self.particles.spawn_hit_flash(event.target_id, duration=0.2)


class ResourceSparkleHandler:
    """Shows sparkles when resources are collected."""

    def __init__(self, particle_system: ParticleSystem):
        self.particles = particle_system
        event_bus.subscribe(ResourceCollectedEvent, self.on_collect)

    def on_collect(self, event: ResourceCollectedEvent) -> None:
        """Show resource collection sparkle (would need position)."""
        # Note: Would need world reference to get position
        pass


class LoggerHandler:
    """Simple handler that logs events to console."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        event_bus.subscribe(DeathEvent, self.on_death)
        if verbose:
            event_bus.subscribe(AttackEvent, self.on_attack)
            event_bus.subscribe(ResourceCollectedEvent, self.on_resource)

    def on_death(self, event: DeathEvent) -> None:
        team_name = "Player" if event.team == 1 else "AI"
        print(f"[EVENT] {event.kind} from {team_name} died at ({event.pos[0]:.1f}, {event.pos[1]:.1f})")

    def on_attack(self, event: AttackEvent) -> None:
        print(f"[ATTACK] Entity {event.attacker_id} hit {event.target_id} for {event.damage} damage")

    def on_resource(self, event: ResourceCollectedEvent) -> None:
        team_name = "Player" if event.team == 1 else "AI"
        print(f"[RESOURCE] {team_name} collected {event.amount} minerals (total: {event.team_total})")


class AILoggerHandler:
    """Logs all AI decisions for debugging."""

    def __init__(self, log_file: Optional[str] = None):
        self.log_file = log_file
        self.logs: List[str] = []
        event_bus.subscribe(AIDecisionEvent, self.on_ai_decision)

    def on_ai_decision(self, event: AIDecisionEvent) -> None:
        timestamp = f"{event.details.get('time', 0):.1f}s" if event.details else "?"
        log_line = f"[AI-{event.team}] [{event.decision_type}] {event.message}"
        self.logs.append(log_line)
        print(log_line)

        # Write to file if specified
        if self.log_file:
            with open(self.log_file, 'a') as f:
                f.write(log_line + '\n')

    def get_recent_logs(self, count: int = 10) -> List[str]:
        """Get most recent log entries."""
        return self.logs[-count:]

    def save_logs(self, filename: str) -> None:
        """Save all logs to a file."""
        with open(filename, 'w') as f:
            for line in self.logs:
                f.write(line + '\n')


@dataclass
class GameMessage:
    """A message to display on the HUD."""
    text: str
    duration: float
    priority: int = 0  # Higher priority messages shown first
    color: str = "#FFFFFF"


class GameMessageSystem:
    """Manages HUD messages (Funksprüche)."""

    def __init__(self):
        self.messages: List[GameMessage] = []
        self.max_messages = 5
        self._mineral_warning_cooldown = 0.0  # Prevent spam
        event_bus.subscribe(MineDepletedEvent, self.on_mine_depleted)
        event_bus.subscribe(BaseUnderAttackEvent, self.on_base_under_attack)
        event_bus.subscribe(InsufficientMineralsEvent, self.on_insufficient_minerals)
        event_bus.subscribe(WorkerWaitingForMineralsEvent, self.on_worker_waiting)
        event_bus.subscribe(UnitReadyEvent, self.on_unit_ready)

    def add_message(self, text: str, duration: float = 5.0, priority: int = 0, color: str = "#FFFFFF") -> None:
        """Add a new message to display."""
        msg = GameMessage(text=text, duration=duration, priority=priority, color=color)
        self.messages.append(msg)
        # Sort by priority (highest first)
        self.messages.sort(key=lambda m: -m.priority)
        # Limit message count
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[:self.max_messages]

    def update(self, dt: float) -> None:
        """Update message timers."""
        for msg in self.messages:
            msg.duration -= dt
        self.messages = [m for m in self.messages if m.duration > 0]
        # Update cooldowns
        if self._mineral_warning_cooldown > 0:
            self._mineral_warning_cooldown -= dt

    def get_messages(self) -> List[GameMessage]:
        """Get current messages for display."""
        return self.messages

    def on_mine_depleted(self, event: MineDepletedEvent) -> None:
        """Handle mine depletion event."""
        if event.team == 1:  # Only show for player
            self.add_message(
                "📻 Die Mine ist leer. Erwarte neuen Auftrag!",
                duration=8.0,
                priority=1,
                color="#FFD700"
            )

    def on_base_under_attack(self, event: BaseUnderAttackEvent) -> None:
        """Handle base attack event."""
        if event.team == 1:  # Only show for player
            self.add_message(
                "⚠️ Feindliche Einheiten in der Basis!",
                duration=5.0,
                priority=10,
                color="#FF4444"
            )

    def on_insufficient_minerals(self, event: InsufficientMineralsEvent) -> None:
        """Handle insufficient minerals when queuing."""
        if event.team == 1 and self._mineral_warning_cooldown <= 0:
            self.add_message(
                f"📻 Wir benötigen mehr Mineralien! ({event.available}/{event.cost})",
                duration=4.0,
                priority=2,
                color="#FF8800"
            )
            self._mineral_warning_cooldown = 3.0  # 3 second cooldown

    def on_worker_waiting(self, event: WorkerWaitingForMineralsEvent) -> None:
        """Handle worker waiting for minerals to build."""
        if event.team == 1 and self._mineral_warning_cooldown <= 0:
            self.add_message(
                f"📻 Wir benötigen mehr Mineralien für {event.building_type}!",
                duration=4.0,
                priority=2,
                color="#FF8800"
            )
            self._mineral_warning_cooldown = 5.0  # 5 second cooldown

    def on_unit_ready(self, event: UnitReadyEvent) -> None:
        """Handle new unit announcement."""
        if event.team == 1:  # Only show for player
            if event.unit_type == "Worker":
                self.add_message(
                    f"📻 Hier ist {event.name}. Melde mich zum Dienst!",
                    duration=4.0,
                    priority=0,
                    color="#88FF88"
                )
            elif event.unit_type == "Soldier":
                phrase = _random.choice(SOLDIER_PHRASES)
                self.add_message(
                    f"📻 {event.rank} {event.name}. {phrase}",
                    duration=4.0,
                    priority=0,
                    color="#88AAFF"
                )


class MusicEventHandler:
    """Handles music transitions based on game events."""

    def __init__(self, music_manager):
        self.music = music_manager
        event_bus.subscribe(BaseUnderAttackEvent, self.on_base_attack)

    def on_base_attack(self, event: BaseUnderAttackEvent) -> None:
        """Switch music when a base is attacked."""
        if event.team == 1:
            # Player base is under attack
            self.music.switch_to_base_attacked()
        else:
            # AI base is under attack (player is attacking)
            self.music.switch_to_attacking_enemy()


class SFXEventHandler:
    """Handles sound effects for game events."""

    def __init__(self, sfx_manager):
        self.sfx = sfx_manager
        self._base_attack_timer = 0.0  # Time since last base attack
        event_bus.subscribe(ResourceCollectedEvent, self.on_resource_collected)
        event_bus.subscribe(ProductionCompletedEvent, self.on_production_completed)
        event_bus.subscribe(UnitReadyEvent, self.on_unit_ready)
        event_bus.subscribe(DeathEvent, self.on_death)
        event_bus.subscribe(AttackEvent, self.on_attack)
        event_bus.subscribe(InsufficientMineralsEvent, self.on_insufficient_minerals)
        event_bus.subscribe(BaseUnderAttackEvent, self.on_base_under_attack)
        event_bus.subscribe(GatheringStartedEvent, self.on_gathering_started)
        event_bus.subscribe(WorkerWaitingForMineralsEvent, self.on_waiting_for_minerals)
        event_bus.subscribe(BuildingConstructionStartEvent, self.on_construction_start)
        event_bus.subscribe(BuildingPlacedEvent, self.on_building_placed)
        event_bus.subscribe(ProductionStartedEvent, self.on_production_started)
        event_bus.subscribe(CommandEvent, self.on_command)

    def on_resource_collected(self, event: ResourceCollectedEvent) -> None:
        """Play sound when minerals are delivered to base."""
        if event.team == 1:  # Only for player
            self.sfx.play('mineral_delivered')

    def on_production_completed(self, event: ProductionCompletedEvent) -> None:
        """Play sound when building completes production."""
        if event.team == 1:  # Only for player
            self.sfx.play('building_complete')

    def on_unit_ready(self, event: UnitReadyEvent) -> None:
        """Play sound when a new unit spawns (includes Funkspruch sound)."""
        if event.team == 1:  # Only for player
            # Stop production loops
            self.sfx.stop_loop('producing_worker')
            self.sfx.stop_loop('producing_soldier')

            # Play Funkspruch sound for announcement
            self.sfx.play('funkspruch')

            # Play unit-specific sound
            if event.unit_type == "Worker":
                self.sfx.play('worker_spawned')
            elif event.unit_type == "Soldier":
                self.sfx.play('soldier_spawned')

    def on_death(self, event: DeathEvent) -> None:
        """Play explosion sound when unit/building dies."""
        if event.kind in ("Base", "Barracks"):
            self.sfx.play('building_destroyed')
        else:
            self.sfx.play('unit_destroyed')

    def on_attack(self, event: AttackEvent) -> None:
        """Play laser shot sound when unit attacks."""
        self.sfx.play('laser_shot')

    def on_insufficient_minerals(self, event: InsufficientMineralsEvent) -> None:
        """Play sound when player lacks minerals for production/building."""
        if event.team == 1:  # Only for player
            self.sfx.play('insufficient_minerals')

    def on_base_under_attack(self, event: BaseUnderAttackEvent) -> None:
        """Start alarm loop when player base is under attack."""
        if event.team == 1:  # Only for player base
            self._base_attack_timer = 12.0  # Reset timer (longer than 10s event cooldown)
            self.sfx.play_loop('base_under_attack')

    def on_gathering_started(self, event: GatheringStartedEvent) -> None:
        """Play mining sound when player worker starts gathering."""
        if event.team == 1:  # Only for player
            self.sfx.play('mineral_mining')

    def on_waiting_for_minerals(self, event: WorkerWaitingForMineralsEvent) -> None:
        """Start waiting alarm when player worker needs minerals for building."""
        if event.team == 1:
            self.sfx.play_loop('waiting_for_minerals')

    def on_construction_start(self, event: BuildingConstructionStartEvent) -> None:
        """Start construction sound when building construction begins."""
        if event.team == 1:
            self.sfx.stop_loop('waiting_for_minerals')  # Stop waiting sound
            self.sfx.play_loop('building_construction')

    def on_building_placed(self, event: BuildingPlacedEvent) -> None:
        """Play reward sound when building is complete."""
        if event.team == 1:
            self.sfx.stop_loop('building_construction')  # Stop construction sound
            self.sfx.play('building_complete_reward')

    def on_production_started(self, event: ProductionStartedEvent) -> None:
        """Start production loop sound based on unit type."""
        if event.team == 1:
            if event.unit_type == "Worker":
                self.sfx.play_loop('producing_worker')
            elif event.unit_type == "Soldier":
                self.sfx.play_loop('producing_soldier')

    def on_command(self, event: CommandEvent) -> None:
        """Play acknowledgment sound when player issues command."""
        if event.team == 1:  # Only for player
            self.sfx.play('command_acknowledged')

    def update(self, dt: float) -> None:
        """Update timers for looping sounds."""
        if self._base_attack_timer > 0:
            self._base_attack_timer -= dt
            if self._base_attack_timer <= 0:
                self.sfx.stop_loop('base_under_attack')
