"""
Particle System
Lightweight particle effects for explosions, sparkles, etc.
"""
import math
import random
from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class Particle:
    """A single particle"""
    x: float
    y: float
    vx: float
    vy: float
    color: str
    lifetime: float
    max_lifetime: float
    size: int = 3

    @property
    def alpha(self) -> float:
        """Fade out as lifetime decreases"""
        return max(0, self.lifetime / self.max_lifetime)

    @property
    def alive(self) -> bool:
        return self.lifetime > 0


class ParticleSystem:
    """Manages all active particles"""

    def __init__(self, max_particles: int = 500):
        self.particles: List[Particle] = []
        self.max_particles = max_particles

    def spawn(
        self,
        x: float,
        y: float,
        angle: float,
        speed: float,
        color: str,
        lifetime: float,
        size: int = 3
    ) -> None:
        """Spawn a new particle"""
        if len(self.particles) >= self.max_particles:
            # Remove oldest particle
            self.particles.pop(0)

        # Convert angle to velocity
        rad = math.radians(angle)
        vx = math.cos(rad) * speed
        vy = math.sin(rad) * speed

        self.particles.append(Particle(
            x=x, y=y,
            vx=vx, vy=vy,
            color=color,
            lifetime=lifetime,
            max_lifetime=lifetime,
            size=size
        ))

    def spawn_burst(
        self,
        x: float,
        y: float,
        count: int,
        min_speed: float,
        max_speed: float,
        colors: List[str],
        min_lifetime: float,
        max_lifetime: float,
        min_size: int = 2,
        max_size: int = 5
    ) -> None:
        """Spawn a burst of particles in random directions"""
        for _ in range(count):
            angle = random.uniform(0, 360)
            speed = random.uniform(min_speed, max_speed)
            color = random.choice(colors)
            lifetime = random.uniform(min_lifetime, max_lifetime)
            size = random.randint(min_size, max_size)

            self.spawn(x, y, angle, speed, color, lifetime, size)

    def update(self, dt: float) -> None:
        """Update all particles"""
        # Update particles
        for p in self.particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.lifetime -= dt

            # Add some gravity/drag
            p.vy += 50 * dt  # Gravity
            p.vx *= 0.98  # Drag
            p.vy *= 0.98

        # Remove dead particles
        self.particles = [p for p in self.particles if p.alive]

    def clear(self) -> None:
        """Remove all particles"""
        self.particles.clear()

    def get_particles(self) -> List[Particle]:
        """Get all active particles for rendering"""
        return self.particles
