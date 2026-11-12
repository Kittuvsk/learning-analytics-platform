# Database Data Dictionary

## 1. Source and scope

This dictionary is generated from the MySQL 8 `information_schema.COLUMNS` export for database `learning_analytics` (`schema_metadata.tsv`). It documents the 25 tables and 203 columns returned by that export.

The definitions below preserve the exported MySQL column types, nullability, defaults, primary-key/unique/index indicators, and auto-increment metadata. Business descriptions are concise interpretations of the column names and project model.

## 2. How to read the constraints

- **PK**: `COLUMN_KEY = PRI` (primary-key column).
- **UQ**: `COLUMN_KEY = UNI` (unique-key column).
- **Indexed**: `COLUMN_KEY = MUL` (non-unique indexed column; this marker alone does not prove that the index is a foreign key).
- **Nullable**: `YES` means the column accepts SQL `NULL`; `NO` means it is mandatory.
- **Default**: `—` means no default was reported for a non-nullable column; `NULL` means SQL NULL is the default/allowed value; other values are the exported MySQL defaults.
- **AUTO_INCREMENT** and generated update behavior are shown where reported by MySQL.

**Foreign-key note:** The column export does not expose referenced table/column names or FK delete/update actions. Use `entity_relationships.md` and `database/schema.sql` for the authoritative FK mapping and relationship cardinalities. Do not infer a foreign key from `MUL` alone.

## 3. Tables

### `activity_events`

Immutable learner activity/event history, including event and receipt timestamps, source references, device and synchronization details.

| Column | MySQL type | Null? | Default | Key | Extra | Description |
|---|---|---:|---|---|---|---|
| event_id | varchar(150) | NO | — | PK | — | Immutable identifier of the activity event. |
| learner_id | varchar(20) | NO | — | Indexed | — | Identifier of the learner. |
| course_id | varchar(20) | NO | — | Indexed | — | Identifier of the course. |
| enrollment_id | varchar(100) | YES | NULL | Indexed | — | Identifier of the learner's course enrollment. |
| content_item_id | bigint unsigned | YES | NULL | Indexed | — | Identifier of the content item. |
| event_type | enum('COURSE_OPENED','CONTENT_VIEWED','VIDEO_PLAYED','VIDEO_COMPLETED','DOCUMENT_DOWNLOADED','QUIZ_STARTED','QUIZ_SUBMITTED','ASSIGNMENT_SUBMITTED','COURSE_COMPLETED','LOGIN','OTHER') | NO | — | Indexed | — | Categorized activity event type. |
| event_time_utc | datetime(6) | NO | — | — | — | Timestamp when the activity occurred, represented as UTC. |
| received_at_utc | datetime(6) | NO | — | — | — | Timestamp when the platform received the event, represented as UTC. |
| learner_timezone | varchar(64) | NO | UTC | — | — | IANA timezone associated with the learner/event. |
| device_type | enum('DESKTOP','MOBILE','TABLET','OTHER') | NO | OTHER | — | — | Device category used for the activity. |
| sync_type | enum('ONLINE','OFFLINE_SYNC') | NO | ONLINE | — | — | Whether the event was recorded online or synchronized later. |
| duration_seconds | int unsigned | NO | 0 | — | — | Activity duration in seconds. |
| source_event_id | varchar(150) | YES | NULL | Indexed | — | Optional source-system event identifier/reference. |
| is_late_event | tinyint(1) | NO | 0 | — | — | Boolean-like flag indicating whether the event is classified as late. |
| created_at | timestamp | NO | CURRENT_TIMESTAMP | — | DEFAULT_GENERATED | Record creation timestamp. |

### `anomaly_records`

Detected data-quality or business-rule anomalies and their review/resolution lifecycle.

| Column | MySQL type | Null? | Default | Key | Extra | Description |
|---|---|---:|---|---|---|---|
| anomaly_id | bigint unsigned | NO | — | PK | auto_increment | Surrogate identifier for the anomaly record. |
| issue_type | enum('DUPLICATE_EVENT','UNENROLLED_ACTIVITY','PREMATURE_COMPLETION','TIMEZONE_MISALIGNMENT','OTHER') | NO | — | Indexed | — | Anomaly category or ground-truth issue classification. |
| entity_type | varchar(50) | NO | — | Indexed | — | Type of entity affected by the anomaly or audit record. |
| entity_id | varchar(150) | NO | — | — | — | Identifier of the affected entity. |
| severity | enum('LOW','MEDIUM','HIGH','CRITICAL') | NO | MEDIUM | — | — | Anomaly severity classification. |
| detection_status | enum('OPEN','REVIEWED','RESOLVED','FALSE_POSITIVE') | NO | OPEN | — | — | Review and resolution state of the anomaly. |
| description | text | YES | NULL | — | — | Optional human-readable description. |
| detected_at | datetime | NO | — | — | — | Timestamp when the anomaly was detected. |
| resolved_at | datetime | YES | NULL | — | — | Optional timestamp when the anomaly was resolved. |

### `assessments`

Assessments configured for courses, including type, scoring thresholds, availability and publication status.

| Column | MySQL type | Null? | Default | Key | Extra | Description |
|---|---|---:|---|---|---|---|
| assessment_id | varchar(30) | NO | — | PK | — | Identifier of the assessment. |
| course_id | varchar(20) | NO | — | Indexed | — | Identifier of the course. |
| content_item_id | bigint unsigned | YES | NULL | Indexed | — | Identifier of the content item. |
| title | varchar(200) | NO | — | — | — | Display title of the assessment or content item. |
| assessment_type | enum('QUIZ','EXAM','ASSIGNMENT','PROJECT') | NO | — | — | — | Assessment category. |
| maximum_score | decimal(8,2) | NO | — | — | — | Maximum score available for the assessment. |
| passing_score | decimal(8,2) | NO | — | — | — | Score threshold required to pass the assessment. |
| is_required | tinyint(1) | NO | 1 | — | — | Whether the assessment is required by the course. |
| available_from | datetime | YES | NULL | — | — | Optional timestamp from which the assessment is available. |
| due_at | datetime | YES | NULL | — | — | Optional assessment due timestamp. |
| assessment_status | enum('DRAFT','PUBLISHED','CLOSED') | NO | DRAFT | — | — | Assessment lifecycle/publication state. |

### `attempts`

Learner assessment attempts, scores, submission state and pass/fail result.

| Column | MySQL type | Null? | Default | Key | Extra | Description |
|---|---|---:|---|---|---|---|
| attempt_id | bigint unsigned | NO | — | PK | auto_increment | Identifier of the assessment attempt. |
| assessment_id | varchar(30) | NO | — | Indexed | — | Identifier of the assessment. |
| learner_id | varchar(20) | NO | — | Indexed | — | Identifier of the learner. |
| enrollment_id | varchar(100) | NO | — | Indexed | — | Identifier of the learner's course enrollment. |
| attempt_number | int unsigned | NO | — | — | — | Sequential attempt number for the learner/enrollment assessment. |
| started_at | datetime | NO | — | — | — | Timestamp when the activity, attempt or process started. |
| submitted_at | datetime | YES | NULL | — | — | Optional timestamp when an attempt was submitted. |
| score | decimal(8,2) | YES | NULL | — | — | Optional score achieved in the attempt. |
| attempt_status | enum('IN_PROGRESS','SUBMITTED','GRADED','ABANDONED') | NO | IN_PROGRESS | — | — | Column used by the table's business or processing workflow. |
| is_passed | tinyint(1) | YES | NULL | — | — | Optional boolean-like pass/fail result. |
| created_at | timestamp | NO | CURRENT_TIMESTAMP | — | DEFAULT_GENERATED | Record creation timestamp. |

### `audit_logs`

Audit trail of user actions and changes to application entities.

| Column | MySQL type | Null? | Default | Key | Extra | Description |
|---|---|---:|---|---|---|---|
| audit_id | bigint unsigned | NO | — | PK | auto_increment | Surrogate identifier for the audit log record. |
| user_id | bigint unsigned | YES | NULL | Indexed | — | Identifier of the application user. |
| action | varchar(100) | NO | — | — | — | Action performed and recorded in the audit log. |
| entity_type | varchar(100) | NO | — | Indexed | — | Type of entity affected by the anomaly or audit record. |
| entity_id | varchar(150) | YES | NULL | — | — | Identifier of the affected entity. |
| old_values | json | YES | NULL | — | — | Optional JSON snapshot of values before the change. |
| new_values | json | YES | NULL | — | — | Optional JSON snapshot of values after the change. |
| ip_address | varchar(45) | YES | NULL | — | — | Optional source IP address associated with the action. |
| created_at | datetime | NO | CURRENT_TIMESTAMP | — | DEFAULT_GENERATED | Record creation timestamp. |

### `cohort_learners`

Effective-dated bridge between cohorts and learners.

| Column | MySQL type | Null? | Default | Key | Extra | Description |
|---|---|---:|---|---|---|---|
| cohort_id | bigint unsigned | NO | — | PK | — | Identifier of the cohort. |
| learner_id | varchar(20) | NO | — | PK | — | Identifier of the learner. |
| joined_at | datetime | NO | CURRENT_TIMESTAMP | PK | DEFAULT_GENERATED | Timestamp when the learner joined the cohort. |
| left_at | datetime | YES | NULL | — | — | Optional timestamp when the learner left the cohort. |

### `cohort_metrics`

Calculated course-level metrics for a cohort and reporting window.

| Column | MySQL type | Null? | Default | Key | Extra | Description |
|---|---|---:|---|---|---|---|
| cohort_metric_id | bigint unsigned | NO | — | PK | auto_increment | Surrogate identifier for the cohort metric record. |
| cohort_id | bigint unsigned | NO | — | Indexed | — | Identifier of the cohort. |
| course_id | varchar(20) | NO | — | Indexed | — | Identifier of the course. |
| window_start | date | NO | — | — | — | Inclusive start date of the metric reporting window. |
| window_end | date | NO | — | — | — | End date of the metric reporting window. |
| enrolled_count | int unsigned | NO | 0 | — | — | Number of enrolled learners in the cohort/course window. |
| active_count | int unsigned | NO | 0 | — | — | Number of active learners in the cohort/course window. |
| completed_count | int unsigned | NO | 0 | — | — | Number of completed learners in the cohort/course window. |
| completion_rate | decimal(6,3) | NO | 0.000 | — | — | Calculated completion proportion/rate for the reporting window. |
| average_engagement_minutes | decimal(12,2) | NO | 0.00 | — | — | Average engagement duration in minutes. |
| calculated_at | datetime | NO | — | — | — | Timestamp when the metric or outcome was calculated. |

### `cohorts`

Learner cohorts with scheduling and lifecycle information.

| Column | MySQL type | Null? | Default | Key | Extra | Description |
|---|---|---:|---|---|---|---|
| cohort_id | bigint unsigned | NO | — | PK | auto_increment | Identifier of the cohort. |
| cohort_code | varchar(50) | NO | — | UQ | — | Unique business code for the cohort. |
| cohort_name | varchar(150) | NO | — | — | — | Display name of the cohort. |
| start_date | date | NO | — | — | — | Column used by the table's business or processing workflow. |
| end_date | date | YES | NULL | — | — | Column used by the table's business or processing workflow. |
| description | varchar(255) | YES | NULL | — | — | Optional human-readable description. |
| cohort_status | enum('PLANNED','ACTIVE','COMPLETED','CANCELLED') | NO | PLANNED | — | — | Lifecycle state of the cohort. |

### `completion_rules`

Versioned, effective-dated rules used to determine course completion.

| Column | MySQL type | Null? | Default | Key | Extra | Description |
|---|---|---:|---|---|---|---|
| completion_rule_id | bigint unsigned | NO | — | PK | auto_increment | Identifier of the completion rule applied to the outcome. |
| course_id | varchar(20) | NO | — | Indexed | — | Identifier of the course. |
| rule_version | int unsigned | NO | — | — | — | Version number of the completion rule. |
| minimum_content_completion | decimal(5,2) | NO | 100.00 | — | — | Minimum content completion percentage required. |
| require_all_assessments | tinyint(1) | NO | 1 | — | — | Whether all required assessments must be completed. |
| minimum_assessment_score | decimal(5,2) | NO | 50.00 | — | — | Minimum assessment score required by the rule. |
| effective_from | datetime | NO | — | — | — | Start of the rule's effective period. |
| effective_to | datetime | YES | NULL | — | — | Optional end of the rule's effective period. |
| rule_status | enum('DRAFT','ACTIVE','RETIRED') | NO | DRAFT | — | — | Column used by the table's business or processing workflow. |
| created_at | timestamp | NO | CURRENT_TIMESTAMP | — | DEFAULT_GENERATED | Record creation timestamp. |

### `content_items`

Hierarchical course content such as modules, videos, documents and assessments.

| Column | MySQL type | Null? | Default | Key | Extra | Description |
|---|---|---:|---|---|---|---|
| content_item_id | bigint unsigned | NO | — | PK | auto_increment | Identifier of the content item. |
| course_id | varchar(20) | NO | — | Indexed | — | Identifier of the course. |
| parent_content_item_id | bigint unsigned | YES | NULL | Indexed | — | Optional parent content item; supports the content hierarchy. |
| title | varchar(200) | NO | — | — | — | Display title of the assessment or content item. |
| content_type | enum('VIDEO','DOCUMENT','ARTICLE','QUIZ','ASSIGNMENT','MODULE') | NO | — | — | — | Type of content item. |
| sequence_number | int unsigned | NO | 1 | — | — | Ordering position within the course/content hierarchy. |
| estimated_minutes | int unsigned | NO | 0 | — | — | Estimated time to complete the content item, in minutes. |
| content_status | enum('DRAFT','PUBLISHED','ARCHIVED') | NO | DRAFT | — | — | Content publication/lifecycle state. |
| created_at | timestamp | NO | CURRENT_TIMESTAMP | — | DEFAULT_GENERATED | Record creation timestamp. |

### `course_outcomes`

Calculated outcome and completion status for an enrollment.

| Column | MySQL type | Null? | Default | Key | Extra | Description |
|---|---|---:|---|---|---|---|
| outcome_id | bigint unsigned | NO | — | PK | auto_increment | Surrogate identifier for the course outcome record. |
| enrollment_id | varchar(100) | NO | — | UQ | — | Identifier of the learner's course enrollment. |
| completion_rule_id | bigint unsigned | YES | NULL | Indexed | — | Identifier of the completion rule applied to the outcome. |
| content_completion_percentage | decimal(5,2) | NO | 0.00 | — | — | Calculated percentage of course content completed. |
| assessment_completion_percentage | decimal(5,2) | NO | 0.00 | — | — | Calculated percentage of required assessments completed. |
| final_assessment_score | decimal(8,2) | YES | NULL | — | — | Optional final/summary assessment score. |
| outcome_status | enum('NOT_STARTED','IN_PROGRESS','COMPLETED','FAILED','WITHDRAWN') | NO | NOT_STARTED | Indexed | — | Calculated enrollment/course outcome state. |
| calculated_at | datetime | NO | — | — | — | Timestamp when the metric or outcome was calculated. |
| completion_reason | varchar(255) | YES | NULL | — | — | Optional explanation for the calculated outcome. |

### `courses`

Course catalogue and course publication/lifecycle information.

| Column | MySQL type | Null? | Default | Key | Extra | Description |
|---|---|---:|---|---|---|---|
| course_id | varchar(20) | NO | — | PK | — | Identifier of the course. |
| course_name | varchar(200) | NO | — | — | — | Display name of the course. |
| description | text | YES | NULL | — | — | Optional human-readable description. |
| category | varchar(100) | YES | NULL | — | — | Optional course category. |
| difficulty_level | enum('BEGINNER','INTERMEDIATE','ADVANCED') | NO | BEGINNER | — | — | Course difficulty classification. |
| course_status | enum('DRAFT','PUBLISHED','ARCHIVED') | NO | DRAFT | Indexed | — | Column used by the table's business or processing workflow. |
| duration_hours | decimal(8,2) | NO | 0.00 | — | — | Estimated course duration in hours. |
| published_at | datetime | YES | NULL | — | — | Optional timestamp when the course was published. |
| created_at | timestamp | NO | CURRENT_TIMESTAMP | — | DEFAULT_GENERATED | Record creation timestamp. |
| updated_at | timestamp | NO | CURRENT_TIMESTAMP | — | DEFAULT_GENERATED on update CURRENT_TIMESTAMP | Most recent record update timestamp. |

### `enrollment_history`

Append-only record of enrollment status transitions and reasons.

| Column | MySQL type | Null? | Default | Key | Extra | Description |
|---|---|---:|---|---|---|---|
| history_id | bigint unsigned | NO | — | PK | auto_increment | Surrogate identifier for the enrollment history record. |
| enrollment_id | varchar(100) | NO | — | Indexed | — | Identifier of the learner's course enrollment. |
| previous_status | varchar(30) | YES | NULL | — | — | Status before the recorded transition. |
| new_status | varchar(30) | NO | — | — | — | Status after the recorded transition. |
| changed_by | bigint unsigned | YES | NULL | Indexed | — | Optional application user who made the change. |
| change_reason | varchar(255) | YES | NULL | — | — | Optional explanation for the status change. |
| changed_at | datetime | NO | CURRENT_TIMESTAMP | — | DEFAULT_GENERATED | Timestamp when the enrollment status change was recorded. |

### `enrollments`

Learner registrations in courses, including cohort association and enrollment lifecycle timestamps.

| Column | MySQL type | Null? | Default | Key | Extra | Description |
|---|---|---:|---|---|---|---|
| enrollment_id | varchar(100) | NO | — | PK | — | Identifier of the learner's course enrollment. |
| learner_id | varchar(20) | NO | — | Indexed | — | Identifier of the learner. |
| course_id | varchar(20) | NO | — | Indexed | — | Identifier of the course. |
| cohort_id | bigint unsigned | YES | NULL | Indexed | — | Identifier of the cohort. |
| enrollment_status | enum('ENROLLED','IN_PROGRESS','COMPLETED','WITHDRAWN','SUSPENDED') | NO | ENROLLED | — | — | Current lifecycle state of the enrollment. |
| enrolled_at | datetime | NO | — | — | — | Timestamp when the learner enrolled in the course. |
| started_at | datetime | YES | NULL | — | — | Timestamp when the activity, attempt or process started. |
| completed_at | datetime | YES | NULL | — | — | Optional timestamp when the enrollment/course was completed. |
| withdrawn_at | datetime | YES | NULL | — | — | Optional timestamp when the enrollment was withdrawn. |
| created_at | timestamp | NO | CURRENT_TIMESTAMP | — | DEFAULT_GENERATED | Record creation timestamp. |
| updated_at | timestamp | NO | CURRENT_TIMESTAMP | — | DEFAULT_GENERATED on update CURRENT_TIMESTAMP | Most recent record update timestamp. |

### `ground_truth`

Expected labels and values for controlled anomaly/test cases; keep separate from model input features.

| Column | MySQL type | Null? | Default | Key | Extra | Description |
|---|---|---:|---|---|---|---|
| ground_truth_id | bigint unsigned | NO | — | PK | auto_increment | Surrogate identifier for the ground-truth record. |
| issue_type | varchar(50) | NO | — | Indexed | — | Anomaly category or ground-truth issue classification. |
| entity_type | varchar(50) | NO | — | — | — | Type of entity affected by the anomaly or audit record. |
| entity_id | varchar(150) | NO | — | — | — | Identifier of the affected entity. |
| expected_label | tinyint(1) | NO | — | — | — | Expected binary/boolean-like label for the controlled case. |
| expected_value | varchar(255) | YES | NULL | — | — | Optional expected value or reference used for validation. |
| explanation | text | YES | NULL | — | — | Human-readable explanation of the expected issue. |
| generator_seed | bigint | NO | — | — | — | Seed recorded for reproducible synthetic generation. |
| created_at | timestamp | NO | CURRENT_TIMESTAMP | — | DEFAULT_GENERATED | Record creation timestamp. |

### `instructor_courses`

Bridge assigning instructors (application users) to courses.

| Column | MySQL type | Null? | Default | Key | Extra | Description |
|---|---|---:|---|---|---|---|
| instructor_user_id | bigint unsigned | NO | — | PK | — | Column used by the table's business or processing workflow. |
| course_id | varchar(20) | NO | — | PK | — | Identifier of the course. |
| assigned_at | datetime | NO | CURRENT_TIMESTAMP | — | DEFAULT_GENERATED | Timestamp when an instructor/role/permission assignment was made. |

### `learners`

Learner profile and lifecycle information, optionally linked to an application user.

| Column | MySQL type | Null? | Default | Key | Extra | Description |
|---|---|---:|---|---|---|---|
| learner_id | varchar(20) | NO | — | PK | — | Identifier of the learner. |
| user_id | bigint unsigned | YES | NULL | UQ | — | Identifier of the application user. |
| first_name | varchar(100) | NO | — | — | — | Learner's first name. |
| last_name | varchar(100) | NO | — | — | — | Learner's last name. |
| email | varchar(255) | NO | — | UQ | — | Email address associated with the user or learner. |
| learner_status | enum('ACTIVE','INACTIVE','SUSPENDED','COMPLETED') | NO | ACTIVE | Indexed | — | Lifecycle state of the learner profile. |
| registration_date | date | NO | — | — | — | Date the learner registered on the platform. |
| timezone | varchar(64) | NO | UTC | — | — | IANA timezone configured for the learner. |
| created_at | timestamp | NO | CURRENT_TIMESTAMP | — | DEFAULT_GENERATED | Record creation timestamp. |
| updated_at | timestamp | NO | CURRENT_TIMESTAMP | — | DEFAULT_GENERATED on update CURRENT_TIMESTAMP | Most recent record update timestamp. |

### `permissions`

Permission catalogue used by role-based access control.

| Column | MySQL type | Null? | Default | Key | Extra | Description |
|---|---|---:|---|---|---|---|
| permission_id | bigint unsigned | NO | — | PK | auto_increment | Identifier of the permission. |
| permission_code | varchar(100) | NO | — | UQ | — | Unique machine-readable permission code. |
| description | varchar(255) | YES | NULL | — | — | Optional human-readable description. |

### `processing_runs`

Execution metadata and record counts for ingestion, validation and analytics pipeline runs.

| Column | MySQL type | Null? | Default | Key | Extra | Description |
|---|---|---:|---|---|---|---|
| processing_run_id | bigint unsigned | NO | — | PK | auto_increment | Surrogate identifier for the processing run. |
| run_code | varchar(100) | NO | — | UQ | — | Unique business identifier for the processing run. |
| process_type | enum('INGESTION','VALIDATION','ANALYTICS','OUTCOME_CALCULATION','FULL_PIPELINE') | NO | — | Indexed | — | Type of pipeline process executed. |
| run_status | enum('STARTED','COMPLETED','FAILED','PARTIAL') | NO | STARTED | — | — | Lifecycle/result state of the processing run. |
| started_at | datetime | NO | — | — | — | Timestamp when the activity, attempt or process started. |
| finished_at | datetime | YES | NULL | — | — | Optional timestamp when the processing run finished. |
| input_record_count | bigint unsigned | NO | 0 | — | — | Number of records received by the process. |
| output_record_count | bigint unsigned | NO | 0 | — | — | Number of records emitted by the process. |
| error_record_count | bigint unsigned | NO | 0 | — | — | Number of records that resulted in errors. |
| configuration | json | YES | NULL | — | — | Optional JSON configuration snapshot for the run. |
| error_summary | text | YES | NULL | — | — | Optional summary of processing errors. |

### `refresh_tokens`

Hashed refresh-token records and revocation/expiry state.

| Column | MySQL type | Null? | Default | Key | Extra | Description |
|---|---|---:|---|---|---|---|
| refresh_token_id | bigint unsigned | NO | — | PK | auto_increment | Surrogate identifier for the refresh-token record. |
| user_id | bigint unsigned | NO | — | Indexed | — | Identifier of the application user. |
| token_hash | varchar(255) | NO | — | UQ | — | Hash of the refresh token; raw refresh tokens should not be stored. |
| expires_at | datetime | NO | — | — | — | Expiry timestamp for the refresh token. |
| revoked_at | datetime | YES | NULL | — | — | Optional timestamp when the refresh token was revoked. |
| created_at | timestamp | NO | CURRENT_TIMESTAMP | — | DEFAULT_GENERATED | Record creation timestamp. |

### `role_permissions`

Bridge assigning permissions to roles.

| Column | MySQL type | Null? | Default | Key | Extra | Description |
|---|---|---:|---|---|---|---|
| role_id | bigint unsigned | NO | — | PK | — | Identifier of the role. |
| permission_id | bigint unsigned | NO | — | PK | — | Identifier of the permission. |

### `roles`

Application role catalogue.

| Column | MySQL type | Null? | Default | Key | Extra | Description |
|---|---|---:|---|---|---|---|
| role_id | bigint unsigned | NO | — | PK | auto_increment | Identifier of the role. |
| role_code | varchar(50) | NO | — | UQ | — | Unique machine-readable role code. |
| role_name | varchar(100) | NO | — | — | — | Display name of the role. |
| description | varchar(255) | YES | NULL | — | — | Optional human-readable description. |
| created_at | timestamp | NO | CURRENT_TIMESTAMP | — | DEFAULT_GENERATED | Record creation timestamp. |

### `user_roles`

Bridge assigning roles to application users.

| Column | MySQL type | Null? | Default | Key | Extra | Description |
|---|---|---:|---|---|---|---|
| user_id | bigint unsigned | NO | — | PK | — | Identifier of the application user. |
| role_id | bigint unsigned | NO | — | PK | — | Identifier of the role. |
| assigned_at | timestamp | NO | CURRENT_TIMESTAMP | — | DEFAULT_GENERATED | Timestamp when an instructor/role/permission assignment was made. |

### `users`

Application login identities, credentials and account status.

| Column | MySQL type | Null? | Default | Key | Extra | Description |
|---|---|---:|---|---|---|---|
| user_id | bigint unsigned | NO | — | PK | auto_increment | Identifier of the application user. |
| username | varchar(100) | NO | — | UQ | — | Unique login username. |
| email | varchar(255) | NO | — | UQ | — | Email address associated with the user or learner. |
| password_hash | varchar(255) | NO | — | — | — | One-way password hash; never store plaintext passwords. |
| full_name | varchar(150) | NO | — | — | — | User's display/full name. |
| account_status | enum('ACTIVE','INACTIVE','LOCKED','PENDING') | NO | PENDING | — | — | Application account lifecycle state. |
| last_login_at | datetime | YES | NULL | — | — | Optional timestamp of the most recent login. |
| created_at | timestamp | NO | CURRENT_TIMESTAMP | — | DEFAULT_GENERATED | Record creation timestamp. |
| updated_at | timestamp | NO | CURRENT_TIMESTAMP | — | DEFAULT_GENERATED on update CURRENT_TIMESTAMP | Most recent record update timestamp. |

### `weekly_engagement_metrics`

Calculated learner-course engagement aggregates by week.

| Column | MySQL type | Null? | Default | Key | Extra | Description |
|---|---|---:|---|---|---|---|
| metric_id | bigint unsigned | NO | — | PK | auto_increment | Surrogate identifier for the weekly engagement metric. |
| learner_id | varchar(20) | NO | — | Indexed | — | Identifier of the learner. |
| course_id | varchar(20) | NO | — | Indexed | — | Identifier of the course. |
| week_start_date | date | NO | — | — | — | Start date identifying the engagement week. |
| active_days | int unsigned | NO | 0 | — | — | Number of distinct active days in the reporting week. |
| valid_event_count | bigint unsigned | NO | 0 | — | — | Count of events retained as valid for engagement calculations. |
| total_engagement_minutes | decimal(12,2) | NO | 0.00 | — | — | Calculated engagement duration in minutes. |
| unique_content_items | int unsigned | NO | 0 | — | — | Number of distinct content items engaged with. |
| calculated_at | datetime | NO | — | — | — | Timestamp when the metric or outcome was calculated. |

## 4. Implementation notes

1. Treat event records and enrollment history as historical records; avoid silently overwriting event/state history.
2. Keep `ground_truth` separate from analytical/model input features. It represents expected labels for controlled validation cases.
3. Store only password hashes in `users.password_hash` and hashed refresh tokens in `refresh_tokens.token_hash`.
4. Apply completion rules using their effective dates and versions; record the rule used when calculating a `course_outcomes` row.
5. Deduplicate activity events before calculating engagement metrics so duplicate events do not inflate counts or duration.
6. Interpret timestamps consistently. Columns explicitly named `_utc` are intended to represent UTC values; keep timezone conversion at ingestion/reporting boundaries.
7. Use the separate entity relationship document and SQL DDL for exact FK definitions, composite-key behavior, and referential actions.

## 5. Source file

- `schema_metadata.tsv` — exported column metadata from MySQL `information_schema.COLUMNS`.
- `../database/schema.sql` — database DDL and seeded RBAC records.
- `entity_relationships.md` — entity relationships and cardinalities.
