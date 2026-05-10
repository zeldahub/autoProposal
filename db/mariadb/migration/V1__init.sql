-- Lon · MariaDB 초기 스키마 (v1)
-- 문자셋: utf8mb4_unicode_ci

SET NAMES utf8mb4;

-- T-01. user
CREATE TABLE IF NOT EXISTS user (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  uuid CHAR(36) NOT NULL UNIQUE,
  email VARCHAR(255) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  display_name VARCHAR(100),
  role ENUM('USER','ADMIN') NOT NULL DEFAULT 'USER',
  last_login_at TIMESTAMP NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- T-02. project
CREATE TABLE IF NOT EXISTS project (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  uuid CHAR(36) NOT NULL UNIQUE,
  owner_id BIGINT NOT NULL,
  company_name VARCHAR(120),
  project_name VARCHAR(200) NOT NULL,
  goal TEXT,
  scope TEXT,
  schedule TEXT,
  organization TEXT,
  staff TEXT,
  cost_dev TEXT,
  cost_ops TEXT,
  license_info TEXT,
  availability TEXT,
  budget VARCHAR(50),
  ai_provider ENUM('OPENAI','GEMINI','ANTHROPIC'),
  ai_model VARCHAR(80),
  status ENUM('DRAFT','READY','GENERATED','ARCHIVED') NOT NULL DEFAULT 'DRAFT',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  deleted_at TIMESTAMP NULL,
  CONSTRAINT fk_project_owner FOREIGN KEY (owner_id) REFERENCES user(id),
  INDEX idx_project_owner (owner_id),
  INDEX idx_project_status (status),
  FULLTEXT KEY ft_project_name (project_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- T-03. project_attachment
CREATE TABLE IF NOT EXISTS project_attachment (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  project_id BIGINT NOT NULL,
  slot ENUM('NOTICE','REFERENCE') NOT NULL,
  filename VARCHAR(255) NOT NULL,
  mime_type VARCHAR(100) NOT NULL,
  size_bytes INT NOT NULL,
  sha256 CHAR(64) NOT NULL,
  storage_path VARCHAR(500) NOT NULL,
  mongo_doc_id CHAR(24),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_attach_project FOREIGN KEY (project_id) REFERENCES project(id),
  INDEX idx_attach_project (project_id),
  UNIQUE KEY uq_attach_sha (project_id, sha256)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- T-04. artifact
CREATE TABLE IF NOT EXISTS artifact (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  project_id BIGINT NOT NULL,
  type ENUM('PPTX','XLSX') NOT NULL,
  version INT NOT NULL,
  filename VARCHAR(255) NOT NULL,
  storage_path VARCHAR(500) NOT NULL,
  size_bytes INT NOT NULL,
  sha256 CHAR(64) NOT NULL,
  llm_call_log_id BIGINT,
  mongo_draft_id CHAR(24),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_artifact_project FOREIGN KEY (project_id) REFERENCES project(id),
  UNIQUE KEY uq_artifact (project_id, type, version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- T-05. ai_provider_setting
CREATE TABLE IF NOT EXISTS ai_provider_setting (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id BIGINT NOT NULL,
  provider ENUM('OPENAI','GEMINI','ANTHROPIC') NOT NULL,
  alias VARCHAR(80),
  api_key_cipher VARBINARY(512) NOT NULL,
  key_iv VARBINARY(16) NOT NULL,
  key_tag VARBINARY(16) NOT NULL,
  default_model VARCHAR(80),
  temperature DECIMAL(3,2) DEFAULT 0.40,
  max_tokens INT,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  last_verified_at TIMESTAMP NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_aiset_user FOREIGN KEY (user_id) REFERENCES user(id),
  UNIQUE KEY uq_aiset (user_id, provider, alias)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- T-06. llm_call_log
CREATE TABLE IF NOT EXISTS llm_call_log (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  project_id BIGINT NOT NULL,
  provider ENUM('OPENAI','GEMINI','ANTHROPIC') NOT NULL,
  model VARCHAR(80) NOT NULL,
  purpose ENUM('ANALYZE','GEN_PPTX','GEN_WBS','TEST') NOT NULL,
  input_tokens INT,
  output_tokens INT,
  latency_ms INT,
  http_status SMALLINT,
  error_code VARCHAR(50),
  mongo_session_id CHAR(24),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_llmlog_project FOREIGN KEY (project_id) REFERENCES project(id),
  INDEX idx_llmlog_project (project_id),
  INDEX idx_llmlog_purpose (purpose)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- T-07. proposal_category
CREATE TABLE IF NOT EXISTS proposal_category (
  id INT AUTO_INCREMENT PRIMARY KEY,
  code VARCHAR(40) NOT NULL UNIQUE,
  name_ko VARCHAR(80) NOT NULL,
  parent_id INT,
  sort_order INT NOT NULL,
  slide_template_key VARCHAR(80),
  system_prompt TEXT,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- T-08. audit_log
CREATE TABLE IF NOT EXISTS audit_log (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id BIGINT,
  action VARCHAR(80) NOT NULL,
  target_type VARCHAR(40),
  target_uuid CHAR(36),
  ip VARCHAR(45),
  user_agent VARCHAR(255),
  meta_json JSON,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_audit_user (user_id),
  INDEX idx_audit_action (action)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
