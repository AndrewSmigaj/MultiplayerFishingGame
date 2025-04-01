import logging
from flask import Blueprint, render_template, current_app

# Import services if needed for specific routes (e.g., admin dashboard)
# from ..game.services.game_service import GameService

log = logging.getLogger(__name__)

# Create a Blueprint for main routes
# Dependencies (like services) would typically be injected when registering the blueprint in app.py
main_bp = Blueprint('main', __name__, template_folder='../templates', static_folder='../static')

@main_bp.route('/')
def index():
    """Serves the main game page."""
    log.info("Serving main game page (index.html)")
    # This assumes the Phaser client will handle everything after loading.
    # We could pass initial data to the template if needed.
    return render_template('index.html')

# Add other HTTP routes here if necessary (e.g., health check, admin endpoints)
@main_bp.route('/health')
def health_check():
    """Basic health check endpoint."""
    log.debug("Health check requested.")
    return {"status": "ok"}, 200

# Example of injecting a dependency (if needed for a route)
# def register_routes(app, game_service: GameService):
#     @main_bp.route('/admin/players')
#     def admin_players():
#         # Use game_service here
#         pass
#     app.register_blueprint(main_bp)
