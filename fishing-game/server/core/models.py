from typing import Optional, List
from pydantic import BaseModel, Field
import uuid

# Using Pydantic for data validation and clear schemas.

class Position(BaseModel):
    """Represents a 2D position in the game world."""
    x: float = 0.0
    y: float = 0.0

class Player(BaseModel):
    """Represents a player in the game."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())) # Unique player ID
    name: str
    position: Position = Field(default_factory=Position)
    state: str = "idle" # e.g., idle, charging, casting, fishing, hooked
    direction: str = "down" # Player facing direction (up, down, left, right)
    fishing_target: Optional[Position] = None # Where the player is currently fishing
    # Add inventory, equipment, etc. later
    # inventory: List[str] = [] # Example: List of item IDs
    # tokens: float = 0.0 # Mock tokens for MVP

class Fish(BaseModel):
    """Represents a fish in the game world."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())) # Unique fish ID
    type: str # e.g., "Bass", "Trout"
    position: Position = Field(default_factory=Position)
    rarity: str # e.g., "Common", "Rare", "Legendary"
    size: float # e.g., length or weight

# Add more models as needed (e.g., Item, Equipment, Transaction)
