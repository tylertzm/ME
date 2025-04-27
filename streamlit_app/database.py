# database.py
# ─────────────────────────────────────────────────────────────────────────────
# MongoDB helper layer for ME-Journal.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List

from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

# ─── connection ─────────────────────────────────────────────────────────────
MONGODB_URI = os.getenv(
    "MONGODB_URI",
    "mongodb+srv://bhanuprasanna2001:3ScAzh6pqL5gObfS@cluster0.jbnxvco.mongodb.net",
)
DB_NAME = "me_journal"
COLL_NAME = "entries"

_client: MongoClient = MongoClient(MONGODB_URI, server_api=ServerApi("1"))
_client.admin.command("ping")

_db: Database = _client[DB_NAME]
_entries: Collection = _db[COLL_NAME]

# ─── public helpers ─────────────────────────────────────────────────────────
def add_entry(prompt: str, structured: Dict[str, Any]) -> str:
    doc = {
        "prompt": prompt,
        "structured": structured,
        "created_at": datetime.utcnow(),
    }
    return str(_entries.insert_one(doc).inserted_id)


def latest_entry() -> Dict[str, Any] | None:
    return _entries.find_one(sort=[("created_at", -1)])


def all_entries() -> List[Dict[str, Any]]:
    return list(_entries.find().sort("created_at", 1))


def search_entries(q: str, limit: int = 10) -> List[Dict[str, Any]]:
    regex = {"$regex": q, "$options": "i"}
    cur = _entries.find(
        {
            "$or": [
                {"prompt": regex},
                {"structured.Mind Space.thought": regex},
            ]
        }
    ).sort("created_at", -1).limit(limit)
    return list(cur)
