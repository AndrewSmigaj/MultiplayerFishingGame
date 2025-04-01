import logging
import sys
from ..config import settings

def setup_logging():
    """Configures application logging."""
    log_level = logging.DEBUG if settings.FLASK_DEBUG else logging.INFO
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # Basic configuration for now
    # Consider using structlog for structured JSON logging later
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout) # Log to console
            # TODO: Add FileHandler for logging to a file in production
            # logging.FileHandler("fishing_game.log")
        ]
    )

    # Example: Quieten noisy libraries
    # logging.getLogger("werkzeug").setLevel(logging.WARNING)
    # logging.getLogger("engineio").setLevel(logging.INFO)
    # logging.getLogger("socketio").setLevel(logging.INFO)

    log = logging.getLogger(__name__)
    log.info(f"Logging configured with level: {logging.getLevelName(log_level)}")

# Call setup_logging() early in your app initialization (e.g., in app.py)
