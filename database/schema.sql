USE learning_analytics;

-- =========================================================
-- 1. AUTHENTICATION AND ROLE-BASED ACCESS CONTROL
-- =========================================================

CREATE TABLE IF NOT EXISTS roles (
    role_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    role_code VARCHAR(50) NOT NULL UNIQUE,
    role_name VARCHAR(100) NOT NULL,
    description VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS permissions (
    permission_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    permission_code VARCHAR(100) NOT NULL UNIQUE,
    description VARCHAR(255)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    account_status ENUM('ACTIVE','INACTIVE','LOCKED','PENDING') NOT NULL DEFAULT 'PENDING',
    last_login_at DATETIME NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS user_roles (
    user_id BIGINT UNSIGNED NOT NULL,
    role_id BIGINT UNSIGNED NOT NULL,
    assigned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, role_id),
    CONSTRAINT fk_user_roles_user FOREIGN KEY (user_id) REFERENCES users(user_id),
    CONSTRAINT fk_user_roles_role FOREIGN KEY (role_id) REFERENCES roles(role_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id BIGINT UNSIGNED NOT NULL,
    permission_id BIGINT UNSIGNED NOT NULL,
    PRIMARY KEY (role_id, permission_id),
    CONSTRAINT fk_role_permissions_role FOREIGN KEY (role_id) REFERENCES roles(role_id),
    CONSTRAINT fk_role_permissions_permission FOREIGN KEY (permission_id) REFERENCES permissions(permission_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS refresh_tokens (
    refresh_token_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    expires_at DATETIME NOT NULL,
    revoked_at DATETIME NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_refresh_tokens_user FOREIGN KEY (user_id) REFERENCES users(user_id),
    INDEX idx_refresh_tokens_user_expiry (user_id, expires_at)
) ENGINE=InnoDB;

-- =========================================================
-- 2. CORE LEARNING ENTITIES
-- =========================================================

CREATE TABLE IF NOT EXISTS learners (
    learner_id VARCHAR(20) PRIMARY KEY,
    user_id BIGINT UNSIGNED NULL UNIQUE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    learner_status ENUM('ACTIVE','INACTIVE','SUSPENDED','COMPLETED') NOT NULL DEFAULT 'ACTIVE',
    registration_date DATE NOT NULL,
    timezone VARCHAR(64) NOT NULL DEFAULT 'UTC',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_learners_user FOREIGN KEY (user_id) REFERENCES users(user_id),
    INDEX idx_learners_status (learner_status)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS courses (
    course_id VARCHAR(20) PRIMARY KEY,
    course_name VARCHAR(200) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    difficulty_level ENUM('BEGINNER','INTERMEDIATE','ADVANCED') NOT NULL DEFAULT 'BEGINNER',
    course_status ENUM('DRAFT','PUBLISHED','ARCHIVED') NOT NULL DEFAULT 'DRAFT',
    duration_hours DECIMAL(8,2) NOT NULL DEFAULT 0,
    published_at DATETIME NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CHECK (duration_hours >= 0),
    INDEX idx_courses_status_category (course_status, category)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS cohorts (
    cohort_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    cohort_code VARCHAR(50) NOT NULL UNIQUE,
    cohort_name VARCHAR(150) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NULL,
    description VARCHAR(255),
    cohort_status ENUM('PLANNED','ACTIVE','COMPLETED','CANCELLED') NOT NULL DEFAULT 'PLANNED',
    CHECK (end_date IS NULL OR end_date >= start_date)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS cohort_learners (
    cohort_id BIGINT UNSIGNED NOT NULL,
    learner_id VARCHAR(20) NOT NULL,
    joined_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    left_at DATETIME NULL,
    PRIMARY KEY (cohort_id, learner_id, joined_at),
    CONSTRAINT fk_cohort_learners_cohort FOREIGN KEY (cohort_id) REFERENCES cohorts(cohort_id),
    CONSTRAINT fk_cohort_learners_learner FOREIGN KEY (learner_id) REFERENCES learners(learner_id),
    CHECK (left_at IS NULL OR left_at >= joined_at),
    INDEX idx_cohort_learners_learner (learner_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS instructor_courses (
    instructor_user_id BIGINT UNSIGNED NOT NULL,
    course_id VARCHAR(20) NOT NULL,
    assigned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (instructor_user_id, course_id),
    CONSTRAINT fk_instructor_courses_user FOREIGN KEY (instructor_user_id) REFERENCES users(user_id),
    CONSTRAINT fk_instructor_courses_course FOREIGN KEY (course_id) REFERENCES courses(course_id)
) ENGINE=InnoDB;

-- =========================================================
-- 3. ENROLLMENTS AND ENROLLMENT HISTORY
-- =========================================================

CREATE TABLE IF NOT EXISTS enrollments (
    enrollment_id VARCHAR(100) PRIMARY KEY,
    learner_id VARCHAR(20) NOT NULL,
    course_id VARCHAR(20) NOT NULL,
    cohort_id BIGINT UNSIGNED NULL,
    enrollment_status ENUM('ENROLLED','IN_PROGRESS','COMPLETED','WITHDRAWN','SUSPENDED') NOT NULL DEFAULT 'ENROLLED',
    enrolled_at DATETIME NOT NULL,
    started_at DATETIME NULL,
    completed_at DATETIME NULL,
    withdrawn_at DATETIME NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_enrollments_learner FOREIGN KEY (learner_id) REFERENCES learners(learner_id),
    CONSTRAINT fk_enrollments_course FOREIGN KEY (course_id) REFERENCES courses(course_id),
    CONSTRAINT fk_enrollments_cohort FOREIGN KEY (cohort_id) REFERENCES cohorts(cohort_id),
    UNIQUE KEY uq_enrollment_learner_course (learner_id, course_id),
    CHECK (started_at IS NULL OR started_at >= enrolled_at),
    CHECK (completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at),
    INDEX idx_enrollments_course_status (course_id, enrollment_status),
    INDEX idx_enrollments_cohort (cohort_id),
    INDEX idx_enrollments_learner (learner_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS enrollment_history (
    history_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    enrollment_id VARCHAR(100) NOT NULL,
    previous_status VARCHAR(30) NULL,
    new_status VARCHAR(30) NOT NULL,
    changed_by BIGINT UNSIGNED NULL,
    change_reason VARCHAR(255),
    changed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_enrollment_history_enrollment FOREIGN KEY (enrollment_id) REFERENCES enrollments(enrollment_id),
    CONSTRAINT fk_enrollment_history_user FOREIGN KEY (changed_by) REFERENCES users(user_id),
    INDEX idx_enrollment_history_enrollment_time (enrollment_id, changed_at)
) ENGINE=InnoDB;

-- =========================================================
-- 4. COURSE CONTENT AND ASSESSMENTS
-- =========================================================

CREATE TABLE IF NOT EXISTS content_items (
    content_item_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    course_id VARCHAR(20) NOT NULL,
    parent_content_item_id BIGINT UNSIGNED NULL,
    title VARCHAR(200) NOT NULL,
    content_type ENUM('VIDEO','DOCUMENT','ARTICLE','QUIZ','ASSIGNMENT','MODULE') NOT NULL,
    sequence_number INT UNSIGNED NOT NULL DEFAULT 1,
    estimated_minutes INT UNSIGNED NOT NULL DEFAULT 0,
    content_status ENUM('DRAFT','PUBLISHED','ARCHIVED') NOT NULL DEFAULT 'DRAFT',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_content_course FOREIGN KEY (course_id) REFERENCES courses(course_id),
    CONSTRAINT fk_content_parent FOREIGN KEY (parent_content_item_id) REFERENCES content_items(content_item_id),
    INDEX idx_content_course_sequence (course_id, sequence_number)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS assessments (
    assessment_id VARCHAR(30) PRIMARY KEY,
    course_id VARCHAR(20) NOT NULL,
    content_item_id BIGINT UNSIGNED NULL,
    title VARCHAR(200) NOT NULL,
    assessment_type ENUM('QUIZ','EXAM','ASSIGNMENT','PROJECT') NOT NULL,
    maximum_score DECIMAL(8,2) NOT NULL,
    passing_score DECIMAL(8,2) NOT NULL,
    is_required BOOLEAN NOT NULL DEFAULT TRUE,
    available_from DATETIME NULL,
    due_at DATETIME NULL,
    assessment_status ENUM('DRAFT','PUBLISHED','CLOSED') NOT NULL DEFAULT 'DRAFT',
    CONSTRAINT fk_assessments_course FOREIGN KEY (course_id) REFERENCES courses(course_id),
    CONSTRAINT fk_assessments_content FOREIGN KEY (content_item_id) REFERENCES content_items(content_item_id),
    CHECK (maximum_score > 0),
    CHECK (passing_score >= 0 AND passing_score <= maximum_score),
    CHECK (due_at IS NULL OR available_from IS NULL OR due_at >= available_from),
    INDEX idx_assessments_course (course_id)
) ENGINE=InnoDB;

-- =========================================================
-- 5. ACTIVITY EVENTS AND ASSESSMENT ATTEMPTS
-- =========================================================

CREATE TABLE IF NOT EXISTS activity_events (
    event_id VARCHAR(150) PRIMARY KEY,
    learner_id VARCHAR(20) NOT NULL,
    course_id VARCHAR(20) NOT NULL,
    enrollment_id VARCHAR(100) NULL,
    content_item_id BIGINT UNSIGNED NULL,
    event_type ENUM(
        'COURSE_OPENED','CONTENT_VIEWED','VIDEO_PLAYED','VIDEO_COMPLETED',
        'DOCUMENT_DOWNLOADED','QUIZ_STARTED','QUIZ_SUBMITTED',
        'ASSIGNMENT_SUBMITTED','COURSE_COMPLETED','LOGIN','OTHER'
    ) NOT NULL,
    event_time_utc DATETIME(6) NOT NULL,
    received_at_utc DATETIME(6) NOT NULL,
    learner_timezone VARCHAR(64) NOT NULL DEFAULT 'UTC',
    device_type ENUM('DESKTOP','MOBILE','TABLET','OTHER') NOT NULL DEFAULT 'OTHER',
    sync_type ENUM('ONLINE','OFFLINE_SYNC') NOT NULL DEFAULT 'ONLINE',
    duration_seconds INT UNSIGNED NOT NULL DEFAULT 0,
    source_event_id VARCHAR(150) NULL,
    is_late_event BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_activity_learner FOREIGN KEY (learner_id) REFERENCES learners(learner_id),
    CONSTRAINT fk_activity_course FOREIGN KEY (course_id) REFERENCES courses(course_id),
    CONSTRAINT fk_activity_enrollment FOREIGN KEY (enrollment_id) REFERENCES enrollments(enrollment_id),
    CONSTRAINT fk_activity_content FOREIGN KEY (content_item_id) REFERENCES content_items(content_item_id),
    CHECK (received_at_utc >= event_time_utc OR is_late_event = TRUE),
    INDEX idx_activity_learner_time (learner_id, event_time_utc),
    INDEX idx_activity_course_time (course_id, event_time_utc),
    INDEX idx_activity_enrollment_time (enrollment_id, event_time_utc),
    INDEX idx_activity_type_time (event_type, event_time_utc),
    INDEX idx_activity_source_event (source_event_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS attempts (
    attempt_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    assessment_id VARCHAR(30) NOT NULL,
    learner_id VARCHAR(20) NOT NULL,
    enrollment_id VARCHAR(100) NOT NULL,
    attempt_number INT UNSIGNED NOT NULL,
    started_at DATETIME NOT NULL,
    submitted_at DATETIME NULL,
    score DECIMAL(8,2) NULL,
    attempt_status ENUM('IN_PROGRESS','SUBMITTED','GRADED','ABANDONED') NOT NULL DEFAULT 'IN_PROGRESS',
    is_passed BOOLEAN NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_attempt_assessment FOREIGN KEY (assessment_id) REFERENCES assessments(assessment_id),
    CONSTRAINT fk_attempt_learner FOREIGN KEY (learner_id) REFERENCES learners(learner_id),
    CONSTRAINT fk_attempt_enrollment FOREIGN KEY (enrollment_id) REFERENCES enrollments(enrollment_id),
    UNIQUE KEY uq_attempt_number (assessment_id, learner_id, attempt_number),
    CHECK (submitted_at IS NULL OR submitted_at >= started_at),
    CHECK (score IS NULL OR score >= 0),
    INDEX idx_attempt_learner_assessment (learner_id, assessment_id)
) ENGINE=InnoDB;

-- =========================================================
-- 6. COMPLETION RULES AND COURSE OUTCOMES
-- =========================================================

CREATE TABLE IF NOT EXISTS completion_rules (
    completion_rule_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    course_id VARCHAR(20) NOT NULL,
    rule_version INT UNSIGNED NOT NULL,
    minimum_content_completion DECIMAL(5,2) NOT NULL DEFAULT 100.00,
    require_all_assessments BOOLEAN NOT NULL DEFAULT TRUE,
    minimum_assessment_score DECIMAL(5,2) NOT NULL DEFAULT 50.00,
    effective_from DATETIME NOT NULL,
    effective_to DATETIME NULL,
    rule_status ENUM('DRAFT','ACTIVE','RETIRED') NOT NULL DEFAULT 'DRAFT',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_completion_rules_course FOREIGN KEY (course_id) REFERENCES courses(course_id),
    UNIQUE KEY uq_course_rule_version (course_id, rule_version),
    CHECK (minimum_content_completion BETWEEN 0 AND 100),
    CHECK (minimum_assessment_score BETWEEN 0 AND 100),
    CHECK (effective_to IS NULL OR effective_to >= effective_from),
    INDEX idx_completion_rules_effective (course_id, rule_status, effective_from)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS course_outcomes (
    outcome_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    enrollment_id VARCHAR(100) NOT NULL UNIQUE,
    completion_rule_id BIGINT UNSIGNED NULL,
    content_completion_percentage DECIMAL(5,2) NOT NULL DEFAULT 0,
    assessment_completion_percentage DECIMAL(5,2) NOT NULL DEFAULT 0,
    final_assessment_score DECIMAL(8,2) NULL,
    outcome_status ENUM('NOT_STARTED','IN_PROGRESS','COMPLETED','FAILED','WITHDRAWN') NOT NULL DEFAULT 'NOT_STARTED',
    calculated_at DATETIME NOT NULL,
    completion_reason VARCHAR(255),
    CONSTRAINT fk_outcomes_enrollment FOREIGN KEY (enrollment_id) REFERENCES enrollments(enrollment_id),
    CONSTRAINT fk_outcomes_rule FOREIGN KEY (completion_rule_id) REFERENCES completion_rules(completion_rule_id),
    CHECK (content_completion_percentage BETWEEN 0 AND 100),
    CHECK (assessment_completion_percentage BETWEEN 0 AND 100),
    INDEX idx_outcomes_status_calculated (outcome_status, calculated_at)
) ENGINE=InnoDB;

-- =========================================================
-- 7. ANALYTICS TABLES
-- =========================================================

CREATE TABLE IF NOT EXISTS weekly_engagement_metrics (
    metric_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    learner_id VARCHAR(20) NOT NULL,
    course_id VARCHAR(20) NOT NULL,
    week_start_date DATE NOT NULL,
    active_days INT UNSIGNED NOT NULL DEFAULT 0,
    valid_event_count BIGINT UNSIGNED NOT NULL DEFAULT 0,
    total_engagement_minutes DECIMAL(12,2) NOT NULL DEFAULT 0,
    unique_content_items INT UNSIGNED NOT NULL DEFAULT 0,
    calculated_at DATETIME NOT NULL,
    CONSTRAINT fk_weekly_learner FOREIGN KEY (learner_id) REFERENCES learners(learner_id),
    CONSTRAINT fk_weekly_course FOREIGN KEY (course_id) REFERENCES courses(course_id),
    UNIQUE KEY uq_weekly_learner_course (learner_id, course_id, week_start_date),
    CHECK (active_days <= 7),
    INDEX idx_weekly_course_week (course_id, week_start_date)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS cohort_metrics (
    cohort_metric_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    cohort_id BIGINT UNSIGNED NOT NULL,
    course_id VARCHAR(20) NOT NULL,
    window_start DATE NOT NULL,
    window_end DATE NOT NULL,
    enrolled_count INT UNSIGNED NOT NULL DEFAULT 0,
    active_count INT UNSIGNED NOT NULL DEFAULT 0,
    completed_count INT UNSIGNED NOT NULL DEFAULT 0,
    completion_rate DECIMAL(6,3) NOT NULL DEFAULT 0,
    average_engagement_minutes DECIMAL(12,2) NOT NULL DEFAULT 0,
    calculated_at DATETIME NOT NULL,
    CONSTRAINT fk_cohort_metrics_cohort FOREIGN KEY (cohort_id) REFERENCES cohorts(cohort_id),
    CONSTRAINT fk_cohort_metrics_course FOREIGN KEY (course_id) REFERENCES courses(course_id),
    CHECK (window_end >= window_start),
    CHECK (completion_rate BETWEEN 0 AND 100),
    INDEX idx_cohort_metrics_period (cohort_id, course_id, window_start, window_end)
) ENGINE=InnoDB;

-- =========================================================
-- 8. ANOMALIES, GROUND TRUTH AND PROCESSING RUNS
-- =========================================================

CREATE TABLE IF NOT EXISTS anomaly_records (
    anomaly_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    issue_type ENUM(
        'DUPLICATE_EVENT','UNENROLLED_ACTIVITY',
        'PREMATURE_COMPLETION','TIMEZONE_MISALIGNMENT','OTHER'
    ) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(150) NOT NULL,
    severity ENUM('LOW','MEDIUM','HIGH','CRITICAL') NOT NULL DEFAULT 'MEDIUM',
    detection_status ENUM('OPEN','REVIEWED','RESOLVED','FALSE_POSITIVE') NOT NULL DEFAULT 'OPEN',
    description TEXT,
    detected_at DATETIME NOT NULL,
    resolved_at DATETIME NULL,
    INDEX idx_anomaly_type_status (issue_type, detection_status),
    INDEX idx_anomaly_entity (entity_type, entity_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS ground_truth (
    ground_truth_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    issue_type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(150) NOT NULL,
    expected_label BOOLEAN NOT NULL,
    expected_value VARCHAR(255) NULL,
    explanation TEXT,
    generator_seed BIGINT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_ground_truth_entity_issue (issue_type, entity_type, entity_id),
    INDEX idx_ground_truth_issue (issue_type)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS processing_runs (
    processing_run_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    run_code VARCHAR(100) NOT NULL UNIQUE,
    process_type ENUM('INGESTION','VALIDATION','ANALYTICS','OUTCOME_CALCULATION','FULL_PIPELINE') NOT NULL,
    run_status ENUM('STARTED','COMPLETED','FAILED','PARTIAL') NOT NULL DEFAULT 'STARTED',
    started_at DATETIME NOT NULL,
    finished_at DATETIME NULL,
    input_record_count BIGINT UNSIGNED NOT NULL DEFAULT 0,
    output_record_count BIGINT UNSIGNED NOT NULL DEFAULT 0,
    error_record_count BIGINT UNSIGNED NOT NULL DEFAULT 0,
    configuration JSON NULL,
    error_summary TEXT NULL,
    CHECK (finished_at IS NULL OR finished_at >= started_at),
    INDEX idx_processing_runs_type_status (process_type, run_status)
) ENGINE=InnoDB;

-- =========================================================
-- 9. AUDIT LOG
-- =========================================================

CREATE TABLE IF NOT EXISTS audit_logs (
    audit_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NULL,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(100) NOT NULL,
    entity_id VARCHAR(150) NULL,
    old_values JSON NULL,
    new_values JSON NULL,
    ip_address VARCHAR(45) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_audit_user FOREIGN KEY (user_id) REFERENCES users(user_id),
    INDEX idx_audit_user_time (user_id, created_at),
    INDEX idx_audit_entity (entity_type, entity_id)
) ENGINE=InnoDB;

-- =========================================================
-- 10. INITIAL ROLE AND PERMISSION SEED
-- =========================================================

INSERT IGNORE INTO roles (role_code, role_name, description) VALUES
('PLATFORM_ADMIN','Platform Administrator','Full platform administration'),
('ACADEMIC_ADMIN','Academic Administrator','Academic configuration and reporting'),
('INSTRUCTOR','Instructor','Assigned course and learner access'),
('SUPPORT_STAFF','Support Staff','Operational support access'),
('LEARNER','Learner','Own learning records and progress');

INSERT IGNORE INTO permissions (permission_code, description) VALUES
('USER_MANAGE','Create and manage platform users'),
('ROLE_MANAGE','Manage roles and permissions'),
('LEARNER_READ_ALL','Read all learner records'),
('LEARNER_READ_OWN','Read own learner record'),
('COURSE_MANAGE','Create and manage courses'),
('COURSE_READ_ASSIGNED','Read assigned courses'),
('ENROLLMENT_MANAGE','Manage enrollments'),
('ACTIVITY_READ','Read learning activity'),
('ASSESSMENT_MANAGE','Manage assessments'),
('ATTEMPT_READ_OWN','Read own assessment attempts'),
('ANALYTICS_READ_ALL','Read platform analytics'),
('ANALYTICS_READ_ASSIGNED','Read assigned-course analytics'),
('SUPPORT_MANAGE','Manage support operations'),
('AUDIT_READ','Read audit logs');

-- Platform Administrator
INSERT IGNORE INTO role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM roles r CROSS JOIN permissions p
WHERE r.role_code = 'PLATFORM_ADMIN';

-- Academic Administrator
INSERT IGNORE INTO role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM roles r
JOIN permissions p ON p.permission_code IN (
    'LEARNER_READ_ALL','COURSE_MANAGE','ENROLLMENT_MANAGE',
    'ACTIVITY_READ','ASSESSMENT_MANAGE','ANALYTICS_READ_ALL','AUDIT_READ'
)
WHERE r.role_code = 'ACADEMIC_ADMIN';

-- Instructor
INSERT IGNORE INTO role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM roles r
JOIN permissions p ON p.permission_code IN (
    'COURSE_READ_ASSIGNED','LEARNER_READ_ALL','ACTIVITY_READ',
    'ASSESSMENT_MANAGE','ANALYTICS_READ_ASSIGNED'
)
WHERE r.role_code = 'INSTRUCTOR';

-- Support Staff
INSERT IGNORE INTO role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM roles r
JOIN permissions p ON p.permission_code IN (
    'LEARNER_READ_ALL','ENROLLMENT_MANAGE','SUPPORT_MANAGE'
)
WHERE r.role_code = 'SUPPORT_STAFF';

-- Learner
INSERT IGNORE INTO role_permissions (role_id, permission_id)
SELECT r.role_id, p.permission_id
FROM roles r
JOIN permissions p ON p.permission_code IN (
    'LEARNER_READ_OWN','ATTEMPT_READ_OWN'
)
WHERE r.role_code = 'LEARNER';