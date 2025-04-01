import logging
import random
from typing import Dict, Optional

# Need to import dependencies that will be injected
# from flask_socketio import SocketIO # Avoid direct import if possible
from .player_manager import PlayerManager
from .fish_manager import FishManager
from ...core.models import Position, Player, Fish
from ..exceptions import PlayerNotFoundException, InvalidActionException

log = logging.getLogger(__name__)

class FishingManager:
    """Manages the state and logic related to active fishing attempts."""

    def __init__(self, player_manager: PlayerManager, fish_manager: FishManager, socketio_instance):
        self.player_manager = player_manager
        self.fish_manager = fish_manager
        self.socketio = socketio_instance # To emit events and start tasks
        self.active_fishing_spots: Dict[str, str] = {} # { "spot_id": player_sid }
        self.fishing_attempts: Dict[str, Dict] = {} # { player_sid: {"spot_id": ..., "end_pos": ...} }
        log.info("FishingManager initialized.")

    # --- Helper Methods (Moved from GameService) ---

    def _calculate_cast_endpoint(self, player_pos: Position, target_pos: Position, power: float) -> Position:
        """Calculates where the line lands based on power."""
        # Simple linear projection for now. Max distance based on power.
        max_cast_distance = 50 + 250 * power # Example: 50 to 300 units
        dx = target_pos.x - player_pos.x
        dy = target_pos.y - player_pos.y
        dist = (dx**2 + dy**2)**0.5

        if dist == 0: # Avoid division by zero if target is same as player pos
            return player_pos

        # Calculate the ratio to scale the vector
        ratio = max_cast_distance / dist
        # Clamp ratio to 1 if target is within max distance
        ratio = min(ratio, 1.0)

        end_x = player_pos.x + dx * ratio
        end_y = player_pos.y + dy * ratio

        # TODO: Add world boundary checks if needed
        return Position(x=end_x, y=end_y)

    def _get_spot_id(self, position: Position, grid_size: int = 50) -> str:
        """Generates a string ID for a fishing spot based on grid cell."""
        grid_x = round(position.x / grid_size)
        grid_y = round(position.y / grid_size)
        return f"{grid_x},{grid_y}"

    # --- Core Fishing Logic Methods ---

    def start_fishing_attempt(self, sid: str, cast_data: dict) -> Optional[Dict]:
        """
        Handles the start_cast event from a client via GameService.
        Checks player state, spot occupation, calculates endpoint, updates state,
        and starts the hook check loop.
        Returns dict with cast details if successful, raises Exception otherwise.
        """
        player = self.player_manager.get_player_by_sid(sid)
        # Player existence check should happen in GameService before calling this

        # Check player state (should be idle)
        if player.state != "idle":
            log.warning(f"Player {player.name} ({sid}) tried to cast while not idle (state: {player.state})")
            raise InvalidActionException("Cannot cast line while not idle.")

        # Validate cast data (moved from GameService for consistency)
        try:
            power = float(cast_data.get('power', 0.5))
            target = Position(**cast_data.get('target', {}))
        except Exception as e:
            log.error(f"Invalid cast_data received from SID {sid}: {cast_data} - Error: {e}")
            raise InvalidActionException("Invalid cast data format.") from e

        # Calculate endpoint, get spot_id
        end_pos = self._calculate_cast_endpoint(player.position, target, power)
        spot_id = self._get_spot_id(end_pos)
        log.info(f"Player {player.name} ({sid}) casting towards {target}, power {power:.2f}. Landing at {end_pos}, spot_id {spot_id}")

        # Check spot occupation
        if spot_id in self.active_fishing_spots:
            occupying_sid = self.active_fishing_spots[spot_id]
            occupying_player = self.player_manager.get_player_by_sid(occupying_sid)
            occupier_name = occupying_player.name if occupying_player else "another player"
            log.info(f"Cast failed for {player.name} ({sid}): Spot {spot_id} occupied by {occupier_name} ({occupying_sid})")
            raise InvalidActionException(f"Fishing spot is occupied by {occupier_name}.")

        # Update player state via player_manager
        log.info(f"Spot {spot_id} is free. Player {player.name} ({sid}) starts fishing.")
        self.active_fishing_spots[spot_id] = sid
        self.fishing_attempts[sid] = {"spot_id": spot_id, "end_pos": end_pos}
        updated_player = self.player_manager.set_player_state(sid, "fishing", fishing_target=end_pos)
        if updated_player:
             # Emit state change using the injected socketio instance
             self.socketio.emit('player_state_changed', {'id': updated_player.id, 'state': updated_player.state}, namespace='/game')
        else:
             # Should not happen if player exists, but handle defensively
             log.error(f"Failed to update player state to 'fishing' for SID {sid}")
             raise PlayerNotFoundException(sid) # Or a different internal error

        # Start background task (hook_check_loop)
        log.debug(f"Starting background task hook_check_loop for SID: {sid}")
        self.socketio.start_background_task(self.hook_check_loop, sid, end_pos)

        # Return details for broadcasting line_casted event
        return {
            "playerId": player.id,
            "startPos": player.position.dict(),
            "endPos": end_pos.dict(),
            "spot_id": spot_id # Keep spot_id internal if not needed by client
        }

    def clear_fishing_attempt(self, sid: str) -> Optional[str]:
        """Cleans up fishing state for a player."""
        log.debug(f"Clearing fishing attempt for SID: {sid}")
        attempt = self.fishing_attempts.pop(sid, None)
        player = self.player_manager.get_player_by_sid(sid) # Get player *before* changing state

        if attempt:
            spot_id = attempt.get("spot_id")
            if spot_id and self.active_fishing_spots.get(spot_id) == sid:
                del self.active_fishing_spots[spot_id]
                log.info(f"Cleared occupied spot {spot_id} for player {player.name if player else sid}")

        player_id = None
        if player and player.state in ["fishing", "hooked"]: # Only reset if they were fishing/hooked
             updated_player = self.player_manager.set_player_state(sid, "idle") # Reset state
             if updated_player:
                  player_id = updated_player.id # Store ID for return
                  # Emit state change using the injected socketio instance
                  self.socketio.emit('player_state_changed', {'id': updated_player.id, 'state': updated_player.state}, namespace='/game')

        # Return player ID for broadcasting line removal
        return player_id

    def hook_check_loop(self, sid: str, end_pos: Position):
        """Background task to periodically check if a fish bites."""
        log.info(f"Starting hook check loop for SID: {sid} at {end_pos}")
        max_attempts = 15 # Try for ~15 seconds
        hook_radius = 25 # How close the fish needs to be
        base_hook_chance = 0.1 # Base chance per check if fish is nearby

        try:
            for attempt in range(max_attempts):
                # Check if player is still fishing at the same spot
                # Accessing self.fishing_attempts directly as we are inside the manager
                current_attempt = self.fishing_attempts.get(sid)
                if not current_attempt or current_attempt['end_pos'] != end_pos:
                    log.info(f"Hook check loop for {sid} aborted (player stopped fishing or cast again).")
                    # No need to call clear_fishing_attempt here, it was likely called already
                    return

                nearby_fish = self.fish_manager.find_nearby_fish(end_pos, hook_radius)
                if nearby_fish:
                    # Simple logic: try to hook the first nearby fish
                    hooked_fish = nearby_fish[0]
                    # Calculate chance based on distance (closer = higher chance)
                    dx = hooked_fish.position.x - end_pos.x
                    dy = hooked_fish.position.y - end_pos.y
                    dist_sq = dx*dx + dy*dy
                    distance_factor = max(0, 1 - (dist_sq**0.5 / hook_radius)) # 1 = very close, 0 = at edge
                    success_threshold = base_hook_chance + (0.4 * distance_factor) # Renamed for clarity
                    roll = random.random() # Generate the random number for this check

                    log.debug(f"Hook check {attempt+1} for {sid}: Fish {hooked_fish.id} nearby. Threshold: {success_threshold:.2f}, Roll: {roll:.2f}")

                    # Emit the update to the client *before* checking success
                    self.socketio.emit('hook_attempt_update', {
                        'threshold': success_threshold,
                        'roll': roll,
                        'attempts_left': max_attempts - attempt,
                        'status': 'checking'
                    }, room=sid, namespace='/game')

                    if roll < success_threshold:
                        log.info(f"Fish hooked for {sid}! Fish: {hooked_fish.type} ({hooked_fish.id})")
                        # Update player state (important to do before clearing attempt)
                        updated_player = self.player_manager.set_player_state(sid, "hooked")
                        if updated_player:
                             # Emit state change using the injected socketio instance
                             self.socketio.emit('player_state_changed', {'id': updated_player.id, 'state': updated_player.state}, namespace='/game')

                        # Store hooked fish details if needed (e.g., in player manager or fishing_attempts)
                        # self.fishing_attempts[sid]['hooked_fish_id'] = hooked_fish.id

                        # Emit event to the player using the stored instance
                        self.socketio.emit('fish_hooked', {'fish': hooked_fish.dict()}, room=sid, namespace='/game')

                        # Clean up the fishing attempt state (spot, etc.)
                        # Note: We don't emit line_removed here, minigame start/end handles that
                        self.clear_fishing_attempt(sid)
                        return # Exit loop

                else:
                     log.debug(f"Hook check {attempt+1} for {sid}: No fish nearby.")
                     # Emit update indicating no fish nearby
                     self.socketio.emit('hook_attempt_update', {
                         'threshold': 0, # Or could send last threshold? Let's send 0
                         'roll': -1, # Invalid roll
                         'attempts_left': max_attempts - attempt,
                         'status': 'no_fish_nearby'
                     }, room=sid, namespace='/game')

                # Wait before next check using the stored instance
                self.socketio.sleep(1)

            # If loop finishes without a hook
            log.info(f"No bite for {sid} after {max_attempts} attempts.")
            # Clear attempt first (which sets state to idle and emits state change via socketio instance)
            player_id = self.clear_fishing_attempt(sid)
            # Then emit failure and line removal
            self.socketio.emit('cast_failed', {'reason': 'No fish bit.'}, room=sid, namespace='/game') # Emit failure only to the player
            if player_id:
                 # Emit line removal to all clients in the namespace
                 self.socketio.emit('line_removed', {'playerId': player_id}, namespace='/game')

        except Exception as e:
            log.exception(f"Error in hook_check_loop for SID {sid}: {e}")
            # Ensure cleanup happens even if there's an error
            player_id = self.clear_fishing_attempt(sid) # This will emit state change to idle
            if player_id:
                 # Emit line removal to all clients in the namespace
                 self.socketio.emit('line_removed', {'playerId': player_id}, namespace='/game')
            # Optionally notify the player of the error
            self.socketio.emit('error', {'message': 'An error occurred during fishing.'}, room=sid, namespace='/game') # Emit error only to the player

    def cancel_fishing(self, sid: str):
        """Handles a player's request to cancel their fishing attempt."""
        player = self.player_manager.get_player_by_sid(sid)
        if not player:
            # Player might have disconnected just before cancelling
            log.warning(f"cancel_fishing called for unknown or disconnected SID: {sid}")
            # No exception needed, just log and exit
            return

        # Check if the player is actually fishing
        if player.state != 'fishing':
            log.warning(f"Player {player.name} ({sid}) tried to cancel fishing but was not in 'fishing' state (state: {player.state})")
            raise InvalidActionException("Cannot cancel cast, not currently fishing.")

        log.info(f"Player {player.name} ({sid}) is cancelling their fishing attempt.")

        # Clear the attempt state (sets state to idle, emits state change)
        player_id = self.clear_fishing_attempt(sid)

        # If clearing was successful (player_id is returned), emit line removal
        if player_id:
            log.debug(f"Emitting line_removed for player {player_id} due to cancellation.")
            self.socketio.emit('line_removed', {'playerId': player_id}, namespace='/game')
        else:
            # This might happen if the state changed between checks, log it.
            log.warning(f"clear_fishing_attempt did not return player_id for {sid} during cancellation, line_removed not emitted.")
