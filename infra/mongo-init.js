// Lon Mongo 초기화 — root 로 실행, lon_app 사용자 생성 후 인덱스
const dbName = 'lon';
const userName = process.env.LON_MONGO_USER || 'lon_app';
const password = process.env.LON_MONGO_PASS || 'CHANGE_ME_LON_2026';

const target = db.getSiblingDB(dbName);
target.createUser({
  user: userName,
  pwd: password,
  roles: [{ role: 'readWrite', db: dbName }],
});

target.createCollection('documents');
target.createCollection('analysisResults');
target.createCollection('llmSessions');
target.createCollection('proposalDrafts');
target.createCollection('wbsTasks');

target.documents.createIndex({ projectUuid: 1, slot: 1 });
target.documents.createIndex({ createdAt: 1 });
target.analysisResults.createIndex({ projectUuid: 1, createdAt: -1 });
target.llmSessions.createIndex({ projectUuid: 1, createdAt: -1 });
target.proposalDrafts.createIndex({ projectUuid: 1, version: -1 });
target.wbsTasks.createIndex({ projectUuid: 1, version: -1 });

print('Lon Mongo init complete: user=' + userName + ' db=' + dbName);
