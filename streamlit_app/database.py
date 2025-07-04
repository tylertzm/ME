# database.py
# ─────────────────────────────────────────────────────────────────────────────
# MongoDB helper layer for ME-Journal – now with delete helpers.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta
from typing import Any, Dict, List

from bson import ObjectId
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

MONGODB_URI = os.getenv(
    "MONGODB_URI",
    "mongodb+srv://bhanuprasanna2001:3ScAzh6pqL5gObfS@cluster0.jbnxvco.mongodb.net/mydatabase?retryWrites=true&w=majority&ssl=true",
)
DB_NAME = "me_journal"
COLL_NAME = "entries"

_client: MongoClient = MongoClient(MONGODB_URI, server_api=ServerApi("1"))
_client.admin.command("ping")

_db: Database = _client[DB_NAME]
_entries: Collection = _db[COLL_NAME]

# ─── public helpers ─────────────────────────────────────────────────────────
def add_entry(prompt: str, structured: Dict[str, Any], journal_date: date | None = None) -> str:
    jd = journal_date or datetime.utcnow().date()
    doc = {
        "prompt": prompt,
        "structured": structured,
        "created_at": datetime.utcnow(),
        "journal_date": jd.isoformat(),
    }
    return str(_entries.insert_one(doc).inserted_id)


def entries_by_date(target: date) -> List[Dict[str, Any]]:
    return list(_entries.find({"journal_date": target.isoformat()}).sort("created_at", 1))


def entries_with_future_events(start: date, days_ahead: int = 60) -> List[Dict[str, Any]]:
    end = start + timedelta(days=days_ahead)
    cur = _entries.find(
        {
            "structured.Schedule.event_date": {"$gte": start.isoformat(), "$lte": end.isoformat()}
        }
    ).sort("structured.Schedule.event_date", 1)
    return list(cur)


def purge_schedule_task(task_key: str) -> int:
    """
    Remove every Schedule item whose task (case-insensitive) matches task_key.
    Returns number of events removed.
    """
    regex = re.compile(f"^{re.escape(task_key)}$", flags=re.IGNORECASE)

    removed = 0
    for doc in _entries.find({"structured.Schedule": {"$exists": True}}):
        sched = doc["structured"].get("Schedule", [])
        cleaned = [ev for ev in sched if not regex.fullmatch(ev["task"].strip())]
        if len(cleaned) != len(sched):
            removed += len(sched) - len(cleaned)
            _entries.update_one({"_id": doc["_id"]}, {"$set": {"structured.Schedule": cleaned}})
    return removed


def purge_relationship(name_key: str) -> int:
    """
    Remove every Relationship item whose name (case-insensitive) matches name_key.
    Returns number of relationships removed.
    """
    regex = re.compile(f"^{re.escape(name_key)}$", flags=re.IGNORECASE)

    removed = 0
    for doc in _entries.find({"structured.Relationships": {"$exists": True}}):
        rels = doc["structured"].get("Relationships", [])
        cleaned = [r for r in rels if not regex.fullmatch(r["name"].strip())]
        if len(cleaned) != len(rels):
            removed += len(rels) - len(cleaned)
            _entries.update_one({"_id": doc["_id"]}, {"$set": {"structured.Relationships": cleaned}})
    return removed


def delete_entry(entry_id: str) -> bool:
    """Delete a whole journal entry by its Mongo ObjectId string."""
    try:
        oid = ObjectId(entry_id)
    except Exception:
        return False
    res = _entries.delete_one({"_id": oid})
    return res.deleted_count == 1


def all_entries() -> List[Dict[str, Any]]:
    return list(_entries.find().sort("created_at", 1))


def latest_entry() -> Dict[str, Any] | None:
    return _entries.find_one(sort=[("created_at", -1)])


def search_entries(q: str, limit: int = 10) -> List[Dict[str, Any]]:
    regex = {"$regex": q, "$options": "i"}
    cur = (
        _entries.find(
            {
                "$or": [
                    {"prompt": regex},
                    {"structured.Mind Space.thought": regex},
                ]
            }
        )
        .sort("created_at", -1)
        .limit(limit)
    )
    return list(cur)
