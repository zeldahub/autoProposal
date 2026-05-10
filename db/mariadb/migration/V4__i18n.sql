-- V4: i18n
-- 1) 사용자별 언어 설정
ALTER TABLE `user`
    ADD COLUMN `locale` VARCHAR(8) NOT NULL DEFAULT 'ko' AFTER `display_name`;

-- 2) 카테고리 영문명 / 영문 시스템 프롬프트
ALTER TABLE `proposal_category`
    ADD COLUMN `name_en` VARCHAR(120) NULL AFTER `name_ko`,
    ADD COLUMN `system_prompt_en` TEXT NULL AFTER `system_prompt`;

-- 기본 영문명 채우기 (V2 시드와 매핑)
UPDATE `proposal_category` SET `name_en` = 'Project Overview' WHERE `code` = 'OVERVIEW';
UPDATE `proposal_category` SET `name_en` = 'General' WHERE `code` = 'GENERAL';
UPDATE `proposal_category` SET `name_en` = 'Technical Requirements' WHERE `code` = 'TECH_REQ';
UPDATE `proposal_category` SET `name_en` = 'Project Management' WHERE `code` = 'PM_REQ';
UPDATE `proposal_category` SET `name_en` = 'Security Requirements' WHERE `code` = 'SECURITY';
UPDATE `proposal_category` SET `name_en` = 'Constraints' WHERE `code` = 'CONSTRAINT';
UPDATE `proposal_category` SET `name_en` = 'Other' WHERE `code` = 'ETC';
