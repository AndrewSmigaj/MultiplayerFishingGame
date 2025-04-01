# Fishing Game

A multiplayer fishing game with blockchain integration (eventually).

## Project Structure

```
fishing-game/
├── server/                 # Python backend (Flask, Flask-SocketIO)
│   ├── app.py              # Entry point, Flask app initialization, DI
│   ├── config.py           # Configuration loading (from .env)
│   ├── requirements.txt    # Python dependencies
│   ├── core/               # Core data models (Pydantic)
│   ├── database/           # Data persistence (MongoDB, Pymongo)
│   │   ├── db_manager.py
│   │   └── repositories/   # Data Access Objects
│   ├── game/               # Game logic
│   │   ├── services/       # High-level orchestration
│   │   ├── managers/       # State management
│   │   └── exceptions.py   # Custom exceptions
│   ├── web/                # Web interfaces
│   │   ├── routes.py       # HTTP endpoints (Flask Blueprints)
│   │   └── sockets.py      # WebSocket event handlers (Flask-SocketIO Namespaces)
│   ├── utils/              # Shared utilities
│   │   └── logging_config.py # Logging setup
│   ├── static/             # Frontend assets (JS, CSS, images)
│   └── templates/          # HTML templates (Jinja2)
├── tests/                  # Automated tests (pytest)
├── .env.example            # Example environment variables
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

## Setup

1.  **Create Environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```
2.  **Install Dependencies:**
    ```bash
    pip install -r server/requirements.txt
    ```
3.  **Configure Environment:**
    *   Copy `.env.example` to `.env`.
    *   Fill in the required values in `.env` (e.g., MongoDB connection string, Flask secret key).
4.  **Run Server:**
    ```bash
    flask run --debug # Or use a production server like gunicorn
    ```

## TODO

*   Implement Phase 1 MVP features.
*   Add detailed API/WebSocket documentation.
