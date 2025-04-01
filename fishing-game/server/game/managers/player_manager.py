import logging
from typing import Dict, Optional
from ...core.models import Player, Position

log = logging.getLogger(__name__)

class PlayerManager:
    """Manages the state of currently connected players in memory."""

    def __init__(self):
        # Store players by their connection SID (SocketIO session ID)
        self.connected_players: Dict[str, Player] = {}
        # Optional: Store by player ID if needed for quick lookups
        # self.players_by_id: Dict[str, Player] = {}

    def add_player(self, sid: str, player: Player):
        """Adds a player associated with a connection SID. Ensures state is idle."""
        if sid in self.connected_players:
            log.warning(f"Player with SID {sid} already exists. Overwriting.")
        player.state = "idle" # Ensure player starts idle
        player.fishing_target = None
        log.info(f"Adding player {player.name} ({player.id}) with SID {sid}, state: {player.state}")
        self.connected_players[sid] = player
        # self.players_by_id[player.id] = player

    def remove_player(self, sid: str) -> Optional[Player]:
        """Removes a player by their connection SID."""
        player = self.connected_players.pop(sid, None)
        if player:
            log.info(f"Removing player {player.name} ({player.id}) with SID {sid}")
            # self.players_by_id.pop(player.id, None)
            return player
        log.warning(f"Attempted to remove non-existent player with SID {sid}")
        return None

    def get_player_by_sid(self, sid: str) -> Optional[Player]:
        """Gets a player by their connection SID."""
        return self.connected_players.get(sid)

    def get_player_state(self, sid: str) -> Optional[str]:
        """Gets the current state of a player by SID."""
        player = self.get_player_by_sid(sid)
        return player.state if player else None

    def set_player_state(self, sid: str, state: str, fishing_target: Optional[Position] = None) -> Optional[Player]:
        """Sets the state and optionally the fishing target of a player by SID."""
        player = self.get_player_by_sid(sid)
        if player:
            log.info(f"Setting player {player.name} ({sid}) state from '{player.state}' to '{state}'")
            player.state = state
            player.fishing_target = fishing_target # Set or clear target
            return player
        log.warning(f"Attempted to set state for non-existent player SID {sid}")
        return None

    # def get_player_by_id(self, player_id: str) -> Optional[Player]:
    #     """Gets a player by their unique player ID."""
    #     return self.players_by_id.get(player_id)

    def update_player_position(self, sid: str, position: Position) -> Optional[Player]:
        """Updates the position of a player identified by SID."""
        player = self.get_player_by_sid(sid)
        if player:
            player.position = position
            log.debug(f"Updated position for player {player.name} ({sid}) to {position}")
            return player
        log.warning(f"Attempted to update position for non-existent player SID {sid}")
        return None

    def update_player_direction(self, sid: str, direction: str) -> Optional[Player]:
        """Updates the facing direction of a player identified by SID."""
        player = self.get_player_by_sid(sid)
        if player:
            if direction in ["up", "down", "left", "right"]: # Basic validation
                player.direction = direction
                log.debug(f"Updated direction for player {player.name} ({sid}) to {direction}")
                return player
            else:
                log.warning(f"Invalid direction '{direction}' received for SID {sid}")
        else:
            log.warning(f"Attempted to update direction for non-existent player SID {sid}")
        return None

    def get_all_players(self) -> list[Player]:
        """Returns a list of all currently connected players."""
        return list(self.connected_players.values())

    def get_other_players(self, sid: str) -> list[Player]:
        """Returns a list of all players except the one with the given SID."""
        return [p for s, p in self.connected_players.items() if s != sid]
