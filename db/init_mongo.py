"""MongoDB 초기화 (init.js 동작과 동일).

사용:
  python db/init_mongo.py
  python db/init_mongo.py --reset
"""
import argparse
import os

from pymongo import ASCENDING, DESCENDING, MongoClient


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument(
        "--uri",
        default=os.getenv("MONGO_URL", "mongodb://lon_app:CHANGE_ME_LON_2026@127.0.0.1:27017/lon?authSource=lon"),
    )
    p.add_argument("--reset", action="store_true")
    return p.parse_args()


def main():
    args = parse_args()
    client = MongoClient(args.uri)
    db = client.get_default_database()

    collections = ["documents", "analysisResults", "llmSessions", "proposalDrafts", "wbsTasks", "categoryPrompts"]

    if args.reset:
        for c in collections:
            db[c].drop()
            print(f"dropped: {c}")

    existing = set(db.list_collection_names())
    for c in collections:
        if c not in existing:
            db.create_collection(c)
            print(f"created: {c}")
        else:
            print(f"exists:  {c}")

    db.documents.create_index([("projectUuid", ASCENDING)])
    db.documents.create_index([("attachmentId", ASCENDING)])
    db.analysisResults.create_index([("projectUuid", ASCENDING)])
    db.llmSessions.create_index([("projectUuid", ASCENDING), ("createdAt", DESCENDING)])
    db.llmSessions.create_index([("purpose", ASCENDING)])
    db.llmSessions.create_index([("createdAt", ASCENDING)], expireAfterSeconds=60 * 60 * 24 * 90)
    db.proposalDrafts.create_index([("projectUuid", ASCENDING), ("version", DESCENDING)])
    db.wbsTasks.create_index([("projectUuid", ASCENDING), ("version", DESCENDING)])
    db.categoryPrompts.create_index([("code", ASCENDING), ("version", DESCENDING)])
    db.categoryPrompts.create_index(
        [("code", ASCENDING)],
        partialFilterExpression={"active": True},
    )
    print("OK indexes created")


if __name__ == "__main__":
    main()
