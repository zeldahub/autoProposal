// Lon · MongoDB 초기화 스크립트
// 실행: mongosh --quiet --file db/mongo/init.js

const dbName = "lon";
db = db.getSiblingDB(dbName);

const collections = [
  "documents",
  "analysisResults",
  "llmSessions",
  "proposalDrafts",
  "wbsTasks",
  "categoryPrompts",
];

for (const c of collections) {
  if (!db.getCollectionNames().includes(c)) {
    db.createCollection(c);
    print(`created: ${c}`);
  } else {
    print(`exists:  ${c}`);
  }
}

// 인덱스
db.documents.createIndex({ projectUuid: 1 });
db.documents.createIndex({ attachmentId: 1 });

db.analysisResults.createIndex({ projectUuid: 1 });

db.llmSessions.createIndex({ projectUuid: 1, createdAt: -1 });
db.llmSessions.createIndex({ purpose: 1 });
db.llmSessions.createIndex({ createdAt: 1 }, { expireAfterSeconds: 60 * 60 * 24 * 90 });

db.proposalDrafts.createIndex({ projectUuid: 1, version: -1 });
db.wbsTasks.createIndex({ projectUuid: 1, version: -1 });
db.categoryPrompts.createIndex({ code: 1, version: -1 });
db.categoryPrompts.createIndex(
  { code: 1 },
  { partialFilterExpression: { active: true } }
);

print("OK indexes created on:", collections.join(", "));
