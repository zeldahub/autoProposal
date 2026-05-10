-- Lon · MariaDB 마이그레이션 (v3) — 인앱 알림
-- 사용자별 알림 (잡 완료/실패, 산출물 생성 완료, 시스템 공지 등)

SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS notification (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id BIGINT NOT NULL,
  type ENUM('GENERATE','JOB','SYSTEM','PROJECT') NOT NULL,
  level ENUM('INFO','SUCCESS','WARN','ERROR') NOT NULL DEFAULT 'INFO',
  title VARCHAR(200) NOT NULL,
  message VARCHAR(500),
  link VARCHAR(255),
  meta_json JSON,
  read_at TIMESTAMP NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_notification_user FOREIGN KEY (user_id) REFERENCES user(id),
  INDEX idx_notif_user_unread (user_id, read_at),
  INDEX idx_notif_user_created (user_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
