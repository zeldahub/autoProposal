"""MongoDB (pymongo) — Lazy 연결."""
from pymongo import MongoClient
from pymongo.database import Database

from app.core.config import settings

_client: MongoClient | None = None


def get_mongo_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(settings.mongo_url, w="majority", journal=True, tz_aware=True)
    return _client


def get_mongo_db() -> Database:
    return get_mongo_client().get_default_database()
