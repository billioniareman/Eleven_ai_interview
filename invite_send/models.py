import os
import logging
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, PyMongoError
from datetime import datetime, timedelta

# Read configuration from environment with sensible defaults for local dev
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.environ.get("MONGO_DB", "eleven_ai")

# Try to connect but fail gracefully — export invite_collection=None when unavailable
invite_collection = None
try:
    # Create the client with reasonable timeouts but don't force a network
    # operation at import time. Creating MongoClient is cheap and lazy — the
    # first network call will happen when we try to read/write. This avoids a
    # noisy stacktrace during module import on machines without Mongo.
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)
    db = client[MONGO_DB]
    # Use a consistent collection name
    invite_collection = db.get_collection('invites')
except Exception:
    # Log a short warning but avoid printing a full stacktrace here — the
    # application routes use defensive helpers that will fall back when
    # `invite_collection` is None.
    logging.warning("Could not initialise MongoDB client for %s; continuing with invite_collection=None", MONGO_URI)


def is_invite_valid(invite_doc):
    """Return True if invite_doc exists, is not used and not expired.

    This function is defensive: it returns False for malformed or missing docs.
    """
    if not invite_doc:
        return False
    try:
        return (
            not invite_doc.get("is_used", False)
            and datetime.utcnow() < invite_doc["expires_at"]
        )
    except Exception:
        logging.exception("Failed while validating invite_doc: %r", invite_doc)
        return False
