# Add print statement at the very top
print("--- Starting server/app.py ---")

import logging
import sys # Import sys to potentially flush output
from flask import Flask, render_template, g # Added g for app context
from flask_socketio import SocketIO
from pymongo.errors import ConnectionFailure

from .config import settings
# Import components
from .utils.logging_config import setup_logging
from .database.db_manager import get_db, close_db_connection
from .database.repositories.player_repository import PlayerRepository
from .game.managers.player_manager import PlayerManager
from .game.managers.fish_manager import FishManager
from .game.managers.fishing_manager import FishingManager # Import new manager
from .game.services.game_service import GameService
from .web.routes import main_bp
from .web.sockets import GameNamespace

# Setup logging
setup_logging()
log = logging.getLogger(__name__)

# Initialize Flask app
# Use static_url_path='' to serve static files from root (e.g., /js/main.js)
# Use static_folder='static' and template_folder='templates' relative to app.py location
app = Flask(__name__, static_url_path='', static_folder='static', template_folder='templates')
app.config['SECRET_KEY'] = settings.FLASK_SECRET_KEY
app.config['DEBUG'] = settings.FLASK_DEBUG

# Initialize Flask-SocketIO
# Consider async_mode='eventlet' or 'gevent' for production
# Add engineio_logger=True for more detailed SocketIO logs if needed
socketio = SocketIO(app, cors_allowed_origins="*", async_mode=None) # Start with default sync mode

# --- Database Connection Handling ---
try:
    # Attempt to get DB connection on startup to catch immediate errors
    db = get_db()
    log.info("Database connection successful on startup.")
except ConnectionFailure as e:
    log.critical(f"CRITICAL: Failed to connect to database on startup: {e}")
    # Depending on requirements, might exit or run in a degraded state
    # For now, we'll let it continue but log critical error
    db = None # Ensure db is None if connection failed

# Teardown app context to close DB connection
# Removing the decorator - connection will close when the process exits.
# @app.teardown_appcontext
def teardown_db(exception=None):
    # This function is no longer automatically called by Flask
    close_db_connection()
    log.debug("Database connection closed.") # Updated log message slightly


# --- Dependency Injection Setup ---
if db is not None: # Correct check for database object
    player_repo = PlayerRepository(db)
    player_manager = PlayerManager()
    fish_manager = FishManager()
    # Instantiate FishingManager, passing dependencies
    fishing_manager = FishingManager(
        player_manager=player_manager,
        fish_manager=fish_manager,
        socketio_instance=socketio
    )
    # Inject FishingManager into GameService
    game_service = GameService(
        player_manager=player_manager,
        fish_manager=fish_manager,
        fishing_manager=fishing_manager, # Pass the instance
        player_repository=player_repo,
        socketio_instance=socketio
    )
else:
    # Handle case where DB connection failed - maybe run without DB features?
    log.error("Running in degraded mode: Database connection failed. Game service not fully initialized.")
    # Set services/repos to None or mock objects if needed for basic functionality
    game_service = None # Or a mock/degraded service


# --- Register Blueprints and SocketIO Namespaces ---
app.register_blueprint(main_bp)
log.info("Registered main blueprint.")

if game_service: # Only register namespace if service initialized correctly
    socketio.on_namespace(GameNamespace('/game', game_service))
    log.info("Registered GameNamespace.")
else:
    log.warning("GameNamespace not registered due to GameService initialization failure.")


# --- Remove Basic SocketIO Handlers (now handled by Namespace) ---
# @socketio.on('connect')
# def handle_connect():
#     """Handles new client connections."""
#     log.info('Client connected')
#     # TODO: Add player management logic (e.g., using PlayerManager)

# @socketio.on('disconnect')
# def handle_disconnect():
    """Handles new client connections."""
    log.info('Client connected')
    # TODO: Add player management logic (e.g., using PlayerManager)

@socketio.on('disconnect')
def handle_disconnect():
    """Handles client disconnections."""
    log.info('Client disconnected')
    # TODO: Add player cleanup logic

# --- Application Runner ---

def run_app():
    """Runs the Flask-SocketIO development server."""
    log.info(f"Starting Flask-SocketIO server (Debug: {settings.FLASK_DEBUG})...")
    print(f"--- Attempting to start SocketIO server on host=0.0.0.0, port=5000, debug={settings.FLASK_DEBUG} ---")
    sys.stdout.flush() # Try flushing stdout before potentially blocking call
    # Use host='0.0.0.0' to make it accessible on the network
    socketio.run(app, host='0.0.0.0', port=5000, debug=settings.FLASK_DEBUG)
    # Note: Flask's default port is 5000. Ensure it doesn't conflict.
    print("--- SocketIO server finished running (should not happen in normal operation) ---") # Should only see if server stops

if __name__ == '__main__':
    print("--- Running main block ---")
    run_app()
    # Consider adding cleanup logic here if needed, e.g., close_db_connection()
