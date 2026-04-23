import os
import motor.motor_asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# MongoDB Configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DATABASE_NAME = "gridseva_db"

class MongoDBManager:
    """Manages MongoDB connections and operations for Ground Truth data."""
    
    def __init__(self, uri: str = MONGODB_URI, db_name: str = DATABASE_NAME):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self.client[db_name]
        self.collection = self.db["ground_truth_faults"]
        print(f"Connected to MongoDB at {uri}, Database: {db_name}")

    async def save_feedback(self, feedback_data: Dict[str, Any]) -> str:
        """
        Saves technician feedback to the ground_truth_faults collection.
        Returns the inserted ID.
        """
        feedback_data["created_at"] = datetime.now()
        result = await self.collection.insert_one(feedback_data)
        return str(result.inserted_id)

    async def get_ground_truth(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieves verified fault records for retraining."""
        cursor = self.collection.find().sort("created_at", -1).limit(limit)
        results = await cursor.to_list(length=limit)
        # Convert ObjectId to string for JSON serialization
        for doc in results:
            doc["_id"] = str(doc["_id"])
        return results

# Singleton instance
db_manager = MongoDBManager()
