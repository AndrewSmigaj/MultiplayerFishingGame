import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings # Import from pydantic_settings
from pydantic import Field # Field can still come from pydantic

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    """Application configuration settings."""
    # Flask settings
    FLASK_SECRET_KEY: str = Field(..., env='FLASK_SECRET_KEY')
    FLASK_DEBUG: bool = Field(False, env='FLASK_DEBUG')

    # MongoDB settings - Load components individually
    MONGO_HOST: str = Field("localhost", env='MONGO_HOST')
    MONGO_PORT: int = Field(27017, env='MONGO_PORT')
    MONGO_USER: str | None = Field(None, env='MONGO_USER') # Optional user
    MONGO_PASSWORD: str | None = Field(None, env='MONGO_PASSWORD') # Optional password
    MONGO_DB_NAME: str = Field('fishing_game', env='MONGO_DB_NAME')

    # Construct the URI from components
    @property
    def MONGO_URI(self) -> str:
        auth_source_db = "admin" # Common auth source for admin user
        if self.MONGO_USER and self.MONGO_PASSWORD:
            # Add authSource parameter
            return f"mongodb://{self.MONGO_USER}:{self.MONGO_PASSWORD}@{self.MONGO_HOST}:{self.MONGO_PORT}/?authSource={auth_source_db}"
        else:
            # No auth needed if no user/pass
            return f"mongodb://{self.MONGO_HOST}:{self.MONGO_PORT}/"

    # Add other settings as needed
    # e.g., SOLANA_RPC_URL: str = Field(None, env='SOLANA_RPC_URL')

    class Config:
        # Load from .env file if present
        env_file = '.env'
        env_file_encoding = 'utf-8'
        # Allow extra fields if needed, though usually better to define all
        # extra = 'allow'

# Create a single instance of settings to be imported elsewhere
settings = Settings()

# Example usage (in other modules):
# from .config import settings
# print(settings.MONGO_URI)
