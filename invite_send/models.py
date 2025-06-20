from pymongo import MongoClient
from datetime import datetime, timedelta

# MongoDB connection
MONGO_URI = "mongodb+srv://admin:4sZf4uIsrlO6GCoV@staging-cluster.olgilw6.mongodb.net/user_management"
client = MongoClient(MONGO_URI)
db = client["interivew"]
invite_collection = db["Invite"]

# Helper for invite validation
def is_invite_valid(invite_doc):
    return (
        not invite_doc.get("is_used", False)
        and datetime.utcnow() < invite_doc["expires_at"]
    )
