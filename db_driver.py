import logging
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from typing import Optional

# Load .env file and MongoDB URI
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

# Logger setup
logger = logging.getLogger("data_base")
logging.basicConfig(level=logging.INFO)

# ---------- MongoDB Connection ----------

try:
    client = MongoClient(MONGO_URI)
    db = client["restaurant"]  # Changed from 'auto_service' to 'restaurant'
    reservations_collection = db["reservations"]  # New collection for reservations
    logger.info("MongoDB connection initialized successfully")
except PyMongoError as e:
    logger.error(f"Error connecting to MongoDB: {e}")
    raise


# ---------- Reservation Database Driver ----------

class DatabaseDriver:
    def __init__(self):
        self.collection = reservations_collection

    def create_reservation(self, name: str, phone: str, date: str, time: str, guests: int) -> Optional[dict]:
        reservation = {
            "name": name,
            "phone": phone,
            "date": date,
            "time": time,
            "guests": guests
        }
        try:
            self.collection.insert_one(reservation)
            logger.info(f"Reservation created for phone: {phone}")
            return reservation
        except PyMongoError as e:
            logger.error(f"Error creating reservation: {e}")
            return None

    def get_reservation_by_phone(self, phone: str) -> Optional[dict]:
        try:
            reservation = self.collection.find_one({"phone": phone})
            if reservation:
                logger.info(f"Reservation found: {phone}")
            else:
                logger.info(f"Reservation not found: {phone}")
            return reservation
        except PyMongoError as e:
            logger.error(f"Error fetching reservation: {e}")
            return None