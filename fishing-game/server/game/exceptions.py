# Custom exceptions for the game logic layer

class GameException(Exception):
    """Base class for game-related exceptions."""
    pass

class PlayerNotFoundException(GameException):
    """Raised when a player cannot be found."""
    def __init__(self, player_id: str):
        self.player_id = player_id
        super().__init__(f"Player with ID '{player_id}' not found.")

class FishNotFoundException(GameException):
    """Raised when a fish cannot be found."""
    def __init__(self, fish_id: str):
        self.fish_id = fish_id
        super().__init__(f"Fish with ID '{fish_id}' not found.")

class InvalidActionException(GameException):
    """Raised when a player attempts an invalid action."""
    pass

# Add more specific exceptions as needed, e.g.,
# class InsufficientTokensException(GameException): pass
# class InventoryFullException(GameException): pass
