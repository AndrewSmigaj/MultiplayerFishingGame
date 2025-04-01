import logging
import random
from typing import Dict, List, Optional
from ...core.models import Fish, Position

log = logging.getLogger(__name__)

# Placeholder for world boundaries or spawn areas
WORLD_WIDTH = 800
WORLD_HEIGHT = 600

class FishManager:
    """Manages the state and spawning of fish in the game world."""

    def __init__(self):
        self.active_fish: Dict[str, Fish] = {}
        # TODO: Add configuration for fish types, rarities, spawn rates, max fish count

    def spawn_initial_fish(self, count: int = 5):
        """Spawns a predefined number of fish on initialization."""
        log.info(f"Spawning {count} initial fish...")
        for _ in range(count):
            # Use placeholder values for now
            self.spawn_fish(fish_type="Bass", rarity="Common", size=random.uniform(5.0, 20.0))
        log.info("Initial fish spawning complete.")

    def spawn_fish(self, fish_type: str, rarity: str, size: float) -> Fish:
        """Spawns a new fish at a random position."""
        # TODO: Implement more sophisticated spawning logic (e.g., specific zones, avoid collisions)
        position = Position(
            x=random.uniform(0, WORLD_WIDTH),
            y=random.uniform(0, WORLD_HEIGHT)
        )
        new_fish = Fish(type=fish_type, position=position, rarity=rarity, size=size)
        self.active_fish[new_fish.id] = new_fish
        log.info(f"Spawned {rarity} {fish_type} ({new_fish.id}) at {position.x:.1f}, {position.y:.1f}")
        return new_fish

    def remove_fish(self, fish_id: str) -> Optional[Fish]:
        """Removes a fish from the world by its ID."""
        fish = self.active_fish.pop(fish_id, None)
        if fish:
            log.info(f"Removed fish {fish.type} ({fish.id})")
            return fish
        log.warning(f"Attempted to remove non-existent fish with ID {fish_id}")
        return None

    def get_fish_by_id(self, fish_id: str) -> Optional[Fish]:
        """Gets a fish by its ID."""
        return self.active_fish.get(fish_id)

    def get_all_fish(self) -> List[Fish]:
        """Returns a list of all currently active fish."""
        return list(self.active_fish.values())

    def update_fish_positions(self, delta_time: float):
        """Updates the positions of all fish (e.g., simple movement)."""
        # TODO: Implement fish movement logic (e.g., random wandering, pathfinding)
        pass # Placeholder for fish movement simulation

    def find_nearby_fish(self, position: Position, radius: float) -> List[Fish]:
        """Finds fish within a certain radius of a position."""
        nearby = []
        for fish in self.active_fish.values():
            # Simple distance calculation (squared distance to avoid sqrt)
            dist_sq = (fish.position.x - position.x)**2 + (fish.position.y - position.y)**2
            if dist_sq <= radius**2:
                nearby.append(fish)
        return nearby

    # TODO: Add methods for managing fish lifecycle, interactions, etc.
