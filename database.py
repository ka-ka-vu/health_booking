from pymongo import MongoClient
from config import MONGO_URI

client = MongoClient(
    MONGO_URI,
    serverSelectionTimeoutMS=5000
)

# Kiểm tra kết nối MongoDB
client.admin.command("ping")

db = client["health_booking"]