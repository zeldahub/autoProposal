-- 표준 목차 시드 (proposal_category)
INSERT INTO proposal_category (code, name_ko, sort_order, is_active) VALUES
  ('OVERVIEW',   '사업 개요',         10, 1),
  ('GENERAL',    '일반 사항',         20, 1),
  ('TECH_REQ',   '기술 요구사항',     30, 1),
  ('PM_REQ',     '사업관리 요구사항', 40, 1),
  ('SECURITY',   '보안 요구사항',     50, 1),
  ('CONSTRAINT', '제약 조건',         60, 1),
  ('ETC',        '기타',              90, 1)
ON DUPLICATE KEY UPDATE
  name_ko=VALUES(name_ko),
  sort_order=VALUES(sort_order),
  is_active=VALUES(is_active);
