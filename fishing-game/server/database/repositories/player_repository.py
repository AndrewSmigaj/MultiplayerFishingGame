import logging
from typing import List, Optional, Dict, Any
from pymongo.database import Database
from pymongo.results import InsertOneResult, UpdateResult, DeleteResult

from .base_repository import BaseRepository
from ...core.models import Player

log = logging.getLogger(__name__)

class PlayerRepository(BaseRepository[Player, str]):
    """Repository for managing Player data in MongoDB."""

    def __init__(self, db: Database):
        super().__init__(db, collection_name="players")

    def get_by_id(self, item_id: str) -> Optional[Player]:
        """Retrieve a player by its ID (UUID string)."""
        log.debug(f"Getting player by id: {item_id}")
        player_data = self.collection.find_one({"id": item_id})
        if player_data:
            # Pydantic can validate the data retrieved from MongoDB
            return Player(**player_data)
        return None

    def get_by_name(self, name: str) -> Optional[Player]:
        """Retrieve a player by name (assuming names are unique for now)."""
        # TODO: Consider if names should be unique and add index if so.
        log.debug(f"Getting player by name: {name}")
        player_data = self.collection.find_one({"name": name})
        if player_data:
            return Player(**player_data)
        return None

    def create(self, item: Player) -> Player:
        """Create a new player."""
        log.debug(f"Creating player: {item.name} ({item.id})")
        # Convert Pydantic model to dict for MongoDB insertion
        player_dict = item.dict()
        result: InsertOneResult = self.collection.insert_one(player_dict)
        # Optionally, you could fetch the inserted document again to ensure consistency
        # For now, we assume the input item is the final state after creation
        log.info(f"Player created with id: {result.inserted_id} (model id: {item.id})")
        return item # Return the original Pydantic model

    def update(self, item_id: str, update_data: Dict[str, Any]) -> Optional[Player]:
        """Update an existing player."""
        log.debug(f"Updating player id {item_id} with data: {update_data}")
        result: UpdateResult = self.collection.update_one(
            {"id": item_id},
            {"$set": update_data}
        )
        if result.matched_count:
            log.info(f"Player {item_id} updated ({result.modified_count} modified).")
            # Return the updated player data
            return self.get_by_id(item_id)
        log.warning(f"Update failed: Player {item_id} not found.")
        return None

    def delete(self, item_id: str) -> bool:
        """Delete a player by its ID."""
        log.debug(f"Deleting player id: {item_id}")
        result: DeleteResult = self.collection.delete_one({"id": item_id})
        if result.deleted_count:
            log.info(f"Player {item_id} deleted.")
            return True
        log.warning(f"Delete failed: Player {item_id} not found.")
        return False

    def list_all(self, filter_query: Optional[Dict[str, Any]] = None) -> List[Player]:
        """List all players, optionally applying a filter."""
        log.debug(f"Listing all players with filter: {filter_query}")
        if filter_query is None:
            filter_query = {}
        players_cursor = self.collection.find(filter_query)
        players = [Player(**data) for data in players_cursor]
        log.info(f"Found {len(players)} players.")
        return players

    # Add specific methods for Player if needed, e.g., find_by_position_range
