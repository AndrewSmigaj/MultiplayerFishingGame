import logging
from flask import request
from flask_socketio import Namespace, emit, join_room, leave_room, disconnect

# Import the main socketio instance created in app.py if needed for emitting outside namespace context
# from ..app import socketio
from ..game.services.game_service import GameService
# Import InvalidActionException as well
from ..game.exceptions import GameException, PlayerNotFoundException, InvalidActionException

log = logging.getLogger(__name__)

# Define the namespace for game-related events
class GameNamespace(Namespace):
    """Handles real-time game events via Socket.IO."""

    def __init__(self, namespace: str, game_service: GameService):
        """
        Initialize the namespace with dependency injection.

        Args:
            namespace: The Socket.IO namespace (e.g., '/game').
            game_service: The injected GameService instance.
        """
        super().__init__(namespace)
        self.game_service = game_service
        log.info(f"GameNamespace initialized for namespace '{namespace}'")

    # --- Connection / Disconnection Events ---

    def on_connect(self):
        """Called when a new client connects to this namespace."""
        sid = request.sid
        log.info(f"Client connected to namespace '{self.namespace}': {sid}")
        # Authentication/Player association usually happens via a separate event (e.g., 'join_game')
        # For now, just log the connection.

    def on_disconnect(self):
        """Called when a client disconnects from this namespace."""
        sid = request.sid
        log.info(f"Client disconnected from namespace '{self.namespace}': {sid}")
        try:
            player = self.game_service.handle_player_disconnect(sid)
            if player:
                # Notify other players that this player left
                emit('player_left', {'id': player.id}, broadcast=True, include_self=False, namespace=self.namespace)
        except GameException as e:
            log.error(f"Error during disconnect for SID {sid}: {e}")
        except Exception as e:
            log.exception(f"Unexpected error during disconnect for SID {sid}: {e}") # Log full traceback

    # --- Custom Game Events ---

    def on_join_game(self, data: dict):
        """Handles a player joining the game world."""
        sid = request.sid
        player_name = data.get('name', f'Player_{sid[:4]}') # Default name if not provided
        log.info(f"SID {sid} attempting to join game as '{player_name}'")

        try:
            # 1. Handle connection logic (create/get player, add to manager)
            player = self.game_service.handle_player_connect(sid, player_name)

            # 2. Send welcome message *only* to the joining player with their data
            emit('welcome', {'player': player.dict()}, room=sid, namespace=self.namespace)
            log.debug(f"Sent 'welcome' to {player_name} ({sid})")

            # 3. Send current world state (other players, fish) to the joining player
            world_state = self.game_service.get_world_state(sid) # Gets state *excluding* self
            emit('world_state', world_state, room=sid, namespace=self.namespace)
            log.debug(f"Sent world state (others) to {player_name} ({sid})")

            # 4. Notify other players about the new player
            emit('player_joined', player.dict(), broadcast=True, include_self=False, namespace=self.namespace)
            log.info(f"Notified others about {player_name} joining.")

            # Optional: Join a room for broadcasting game updates
            # join_room(player.id) # Or a general 'game_world' room

        except GameException as e:
            log.error(f"Game error during join_game for SID {sid}: {e}")
            emit('error', {'message': str(e)}, room=sid, namespace=self.namespace)
            # Optionally disconnect if join fails critically
            # disconnect(sid)
        except Exception as e:
            log.exception(f"Unexpected error during join_game for SID {sid}: {e}")
            emit('error', {'message': 'An internal server error occurred.'}, room=sid, namespace=self.namespace)
            # disconnect(sid)


    def on_player_move(self, data: dict):
        """Handles player movement updates from a client."""
        sid = request.sid
        log.debug(f"Received player_move from SID {sid}: {data}")
        try:
            updated_player = self.game_service.handle_player_move(sid, data)
            if updated_player:
                # Broadcast the updated position to other players
                emit('player_moved', updated_player.dict(), broadcast=True, include_self=False, namespace=self.namespace)
        except PlayerNotFoundException:
             log.warning(f"Move event from unknown SID: {sid}")
             # Decide if an error should be sent back or just ignored
        except GameException as e:
            log.error(f"Game error during player_move for SID {sid}: {e}")
            emit('error', {'message': str(e)}, room=sid, namespace=self.namespace)
        except Exception as e:
            log.exception(f"Unexpected error during player_move for SID {sid}: {e}")
            emit('error', {'message': 'An internal server error occurred processing movement.'}, room=sid, namespace=self.namespace)

    def on_player_face(self, data: dict):
        """Handles player changing facing direction."""
        sid = request.sid
        log.debug(f"Received player_face from SID {sid}: {data}")
        try:
            updated_player = self.game_service.handle_player_face(sid, data)
            if updated_player:
                # Broadcast the new direction to other players
                emit('player_faced', {'id': updated_player.id, 'direction': updated_player.direction},
                     broadcast=True, include_self=False, namespace=self.namespace)
        except PlayerNotFoundException:
            log.warning(f"Face event from unknown SID: {sid}")
            # Optionally emit error back if needed
            # emit('error', {'message': 'Cannot change direction: Player not found.'}, room=sid, namespace=self.namespace)
        except InvalidActionException as e:
            log.warning(f"Invalid face attempt by SID {sid}: {e}")
            emit('error', {'message': str(e)}, room=sid, namespace=self.namespace)
        except GameException as e: # Catch other potential game logic errors if any
            log.error(f"Game error during player_face for SID {sid}: {e}")
            emit('error', {'message': str(e)}, room=sid, namespace=self.namespace)
        except Exception as e:
            log.exception(f"Unexpected error during player_face for SID {sid}: {e}")
            emit('error', {'message': 'Internal server error processing direction.'}, room=sid, namespace=self.namespace)


    # --- Cast Handling ---
    def on_start_cast(self, data: dict):
        """Handles player initiating a cast after charging."""
        sid = request.sid
        log.debug(f"Received start_cast from SID {sid}: {data}")
        try:
            # Call the service layer to handle the core logic
            cast_details = self.game_service.handle_start_cast(sid, data)

            # If successful, broadcast the line being cast
            if cast_details:
                emit('line_casted', cast_details, broadcast=True, include_self=True, namespace=self.namespace)
                log.info(f"Broadcasted line_casted for player {cast_details.get('playerId')}")
                # TODO: Start the hook check loop in GameService
                # This might involve importing socketio from app and using:
                # from ..app import socketio
                # socketio.start_background_task(self.game_service.hook_check_loop, sid, cast_details['endPos'])

        except PlayerNotFoundException:
            # This case might indicate a sync issue or unexpected event order
            log.warning(f"start_cast event from unknown SID: {sid}")
            # Optionally emit an error back to the sender if helpful
            # emit('error', {'message': 'Cannot cast: Player not found.'}, room=sid, namespace=self.namespace)
        except InvalidActionException as e:
            # Handle specific failures like spot occupied or wrong state
            log.warning(f"Invalid cast attempt by SID {sid}: {e}")
            emit('cast_failed', {'reason': str(e)}, room=sid, namespace=self.namespace)
        except GameException as e:
            # Catch other general game logic errors
            log.error(f"Game error during start_cast for SID {sid}: {e}")
            emit('error', {'message': str(e)}, room=sid, namespace=self.namespace)
        except Exception as e:
            # Catch unexpected errors
            log.exception(f"Unexpected error during start_cast for SID {sid}: {e}")
            emit('error', {'message': 'An internal server error occurred while casting.'}, room=sid, namespace=self.namespace)

    def on_cancel_cast(self):
        """Handles player request to cancel their current fishing attempt."""
        sid = request.sid
        log.debug(f"Received cancel_cast from SID {sid}")
        try:
            # Call the service layer to handle the cancellation
            self.game_service.handle_cancel_cast(sid)
            # No specific confirmation needed unless there's an error
            log.info(f"Player {sid} cancelled their cast.")
            # The service layer should handle emitting 'line_removed' and 'player_state_changed'

        except PlayerNotFoundException:
            log.warning(f"cancel_cast event from unknown SID: {sid}")
            # No error sent back, as the client likely already handled UI locally
        except InvalidActionException as e:
            # Handle cases where cancellation isn't valid (e.g., not fishing)
            log.warning(f"Invalid cancel_cast attempt by SID {sid}: {e}")
            # Optionally send an error back if needed, but might be noisy
            # emit('error', {'message': str(e)}, room=sid, namespace=self.namespace)
        except GameException as e:
            log.error(f"Game error during cancel_cast for SID {sid}: {e}")
            emit('error', {'message': str(e)}, room=sid, namespace=self.namespace)
        except Exception as e:
            log.exception(f"Unexpected error during cancel_cast for SID {sid}: {e}")
            emit('error', {'message': 'An internal server error occurred while cancelling cast.'}, room=sid, namespace=self.namespace)


    # --- Minigame Handling ---
    def on_minigame_update(self, data: dict):
        """Handles updates during the fishing minigame."""
        sid = request.sid
        log.debug(f"Received minigame_update from SID {sid}: {data}")
        try:
            # GameService handles the minigame logic and outcome
            self.game_service.handle_minigame_update(sid, data)
            # Success/failure events would likely be emitted from within the GameService
            # based on the minigame outcome.
        except PlayerNotFoundException:
             log.warning(f"Minigame update from unknown SID: {sid}")
        except GameException as e:
            log.error(f"Game error during minigame_update for SID {sid}: {e}")
            emit('error', {'message': str(e)}, room=sid, namespace=self.namespace)
        except Exception as e:
            log.exception(f"Unexpected error during minigame_update for SID {sid}: {e}")
            emit('error', {'message': 'An internal server error occurred during minigame.'}, room=sid, namespace=self.namespace)


# TODO: Add more event handlers as needed (chat, interactions, etc.)
