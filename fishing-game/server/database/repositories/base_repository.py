from abc import ABC, abstractmethod
from typing import TypeVar, Generic, List, Optional, Any, Dict
from pymongo.database import Database
from pydantic import BaseModel

# Define generic types for the model and its ID
ModelType = TypeVar('ModelType', bound=BaseModel)
IDType = TypeVar('IDType') # Typically str or ObjectId

class BaseRepository(Generic[ModelType, IDType], ABC):
    """Abstract base class for data repositories."""

    def __init__(self, db: Database, collection_name: str):
        """
        Initialize the repository.

        Args:
            db: The pymongo database instance.
            collection_name: The name of the MongoDB collection.
        """
        self.db = db
        self.collection = self.db[collection_name]

    @abstractmethod
    def get_by_id(self, item_id: IDType) -> Optional[ModelType]:
        """Retrieve an item by its ID."""
        pass

    @abstractmethod
    def create(self, item: ModelType) -> ModelType:
        """Create a new item."""
        pass

    @abstractmethod
    def update(self, item_id: IDType, update_data: Dict[str, Any]) -> Optional[ModelType]:
        """Update an existing item."""
        pass

    @abstractmethod
    def delete(self, item_id: IDType) -> bool:
        """Delete an item by its ID. Returns True if deleted, False otherwise."""
        pass

    @abstractmethod
    def list_all(self, filter_query: Optional[Dict[str, Any]] = None) -> List[ModelType]:
        """List all items, optionally applying a filter."""
        pass

    # You can add more common methods here, e.g., find_one_by_field
