

\# Learning Analytics Platform

\# Entity Relationship Documentation



\## 1. Introduction



This document describes the database structure of the Learning Analytics Platform.



The database uses MySQL 8 and contains 25 relational tables.



The database is organized into the following functional areas:



1\. Authentication and Role-Based Access Control

2\. Core Learning Entities

3\. Enrollments and Enrollment History

4\. Course Content and Assessments

5\. Activity Events and Assessment Attempts

6\. Completion Rules and Course Outcomes

7\. Analytics and Reporting

8\. Anomaly Detection and Processing

9\. Audit Logging



\## 2. Database Entities



\### 2.1 Authentication and RBAC



\*\*1. roles\*\*

\- Primary Key: role\_id

\- Unique field: role\_code

\- Stores platform roles.

\- Example roles: PLATFORM\_ADMIN, ACADEMIC\_ADMIN, INSTRUCTOR, SUPPORT\_STAFF, LEARNER.



\*\*2. permissions\*\*

\- Primary Key: permission\_id

\- Unique field: permission\_code

\- Stores individual permissions available in the platform.



\*\*3. users\*\*

\- Primary Key: user\_id

\- Unique fields: username, email

\- Stores login credentials and account information.

\- Passwords are stored as password hashes.



\*\*4. user\_roles\*\*

\- Composite Primary Key: user\_id, role\_id

\- Foreign Keys: user\_id references users, role\_id references roles.

\- Connects users with their assigned roles.



\*\*5. role\_permissions\*\*

\- Composite Primary Key: role\_id, permission\_id

\- Foreign Keys: role\_id references roles, permission\_id references permissions.

\- Connects roles with their permitted actions.



\*\*6. refresh\_tokens\*\*

\- Primary Key: refresh\_token\_id

\- Foreign Key: user\_id references users.

\- Stores hashed refresh tokens, expiration dates and revocation details.



\### 2.2 Core Learning Entities



\*\*7. learners\*\*

\- Primary Key: learner\_id

\- Foreign Key: user\_id references users.

\- Stores learner profile information, status, registration date and timezone.

\- user\_id is nullable and unique.



\*\*8. courses\*\*

\- Primary Key: course\_id

\- Stores course name, description, category, difficulty, status and duration.



\*\*9. cohorts\*\*

\- Primary Key: cohort\_id

\- Unique field: cohort\_code

\- Stores learner groups and their start and end dates.



\*\*10. cohort\_learners\*\*

\- Composite Primary Key: cohort\_id, learner\_id, joined\_at

\- Foreign Keys: cohort\_id references cohorts, learner\_id references learners.

\- Maintains learner membership history within cohorts.



\*\*11. instructor\_courses\*\*

\- Composite Primary Key: instructor\_user\_id, course\_id

\- Foreign Keys: instructor\_user\_id references users, course\_id references courses.

\- Stores instructor-to-course assignments.



\### 2.3 Enrollments and Enrollment History



\*\*12. enrollments\*\*

\- Primary Key: enrollment\_id

\- Foreign Keys:

&#x20; - learner\_id references learners

&#x20; - course\_id references courses

&#x20; - cohort\_id references cohorts

\- Stores learner enrollment details and lifecycle status.

\- Unique constraint: learner\_id and course\_id.

\- Tracks enrollment, start, completion and withdrawal dates.



\*\*13. enrollment\_history\*\*

\- Primary Key: history\_id

\- Foreign Keys:

&#x20; - enrollment\_id references enrollments

&#x20; - changed\_by references users

\- Records previous status, new status, reason and change timestamp.



\### 2.4 Course Content and Assessments



\*\*14. content\_items\*\*

\- Primary Key: content\_item\_id

\- Foreign Keys:

&#x20; - course\_id references courses

&#x20; - parent\_content\_item\_id references content\_items

\- Stores course content such as modules, videos, documents and articles.

\- Supports hierarchical content through parent-child relationships.



\*\*15. assessments\*\*

\- Primary Key: assessment\_id

\- Foreign Keys:

&#x20; - course\_id references courses

&#x20; - content\_item\_id references content\_items

\- Stores quizzes, exams, assignments and projects.

\- Includes maximum score, passing score and assessment status.



\### 2.5 Activity Events and Attempts



\*\*16. activity\_events\*\*

\- Primary Key: event\_id

\- Foreign Keys:

&#x20; - learner\_id references learners

&#x20; - course\_id references courses

&#x20; - enrollment\_id references enrollments

&#x20; - content\_item\_id references content\_items

\- Stores learner activities such as course opening, content viewing, video completion and assessment activity.

\- Maintains event timestamps, received timestamps, timezone, device and synchronization details.

\- enrollment\_id and content\_item\_id are nullable.



\*\*17. attempts\*\*

\- Primary Key: attempt\_id

\- Foreign Keys:

&#x20; - assessment\_id references assessments

&#x20; - learner\_id references learners

&#x20; - enrollment\_id references enrollments

\- Stores assessment attempts, scores, attempt numbers and grading status.

\- Unique constraint: assessment\_id, learner\_id and attempt\_number.



\### 2.6 Completion Rules and Outcomes



\*\*18. completion\_rules\*\*

\- Primary Key: completion\_rule\_id

\- Foreign Key: course\_id references courses.

\- Stores course completion requirements.

\- Supports rule versions and effective dates.



\*\*19. course\_outcomes\*\*

\- Primary Key: outcome\_id

\- Foreign Keys:

&#x20; - enrollment\_id references enrollments

&#x20; - completion\_rule\_id references completion\_rules

\- Stores calculated course completion results.

\- enrollment\_id is unique, allowing one outcome record per enrollment.



\### 2.7 Analytics and Reporting



\*\*20. weekly\_engagement\_metrics\*\*

\- Primary Key: metric\_id

\- Foreign Keys:

&#x20; - learner\_id references learners

&#x20; - course\_id references courses

\- Stores weekly learner engagement information.

\- Unique constraint: learner\_id, course\_id and week\_start\_date.



\*\*21. cohort\_metrics\*\*

\- Primary Key: cohort\_metric\_id

\- Foreign Keys:

&#x20; - cohort\_id references cohorts

&#x20; - course\_id references courses

\- Stores cohort-level analytics.

\- Includes enrollment count, active count, completion count and engagement metrics.



\### 2.8 Anomalies and Processing



\*\*22. anomaly\_records\*\*

\- Primary Key: anomaly\_id

\- Stores detected data anomalies.

\- Includes issue type, entity type, entity ID, severity and resolution status.

\- Uses entity\_type and entity\_id to identify affected records.



\*\*23. ground\_truth\*\*

\- Primary Key: ground\_truth\_id

\- Unique combination: issue\_type, entity\_type and entity\_id.

\- Stores expected anomaly labels and expected values.

\- Used to validate anomaly detection results.



\*\*24. processing\_runs\*\*

\- Primary Key: processing\_run\_id

\- Unique field: run\_code

\- Tracks ingestion, validation, analytics and outcome calculation runs.

\- Stores run status, input count, output count and error count.



\### 2.9 Audit Logging



\*\*25. audit\_logs\*\*

\- Primary Key: audit\_id

\- Foreign Key: user\_id references users.

\- Stores user actions, affected entities, old values, new values and timestamps.

\- Supports traceability and auditing.



\## 3. Entity Relationships and Cardinality



\### 3.1 Authentication Relationships



| Relationship | Cardinality |

|---|---|

| Users to User Roles | One-to-Many |

| Roles to User Roles | One-to-Many |

| Roles to Role Permissions | One-to-Many |

| Permissions to Role Permissions | One-to-Many |

| Users to Refresh Tokens | One-to-Many |

| Users to Learners | One-to-Zero-or-One |



Users and roles have a Many-to-Many relationship through user\_roles.



Roles and permissions have a Many-to-Many relationship through role\_permissions.



\### 3.2 Learning Relationships



| Relationship | Cardinality |

|---|---|

| Learners to Enrollments | One-to-Many |

| Courses to Enrollments | One-to-Many |

| Cohorts to Enrollments | One-to-Many (optional) |

| Learners to Cohort Learners | One-to-Many |

| Cohorts to Cohort Learners | One-to-Many |

| Users to Instructor Courses | One-to-Many |

| Courses to Instructor Courses | One-to-Many |



Learners and cohorts have a Many-to-Many relationship through cohort\_learners.



Instructors and courses have a Many-to-Many relationship through instructor\_courses.



\### 3.3 Course Content and Assessment Relationships



| Relationship | Cardinality |

|---|---|

| Courses to Content Items | One-to-Many |

| Content Items to Child Content Items | One-to-Many |

| Courses to Assessments | One-to-Many |

| Content Items to Assessments | One-to-Many (optional) |

| Assessments to Attempts | One-to-Many |



A course can contain multiple content items and assessments.



Content items can have parent-child relationships to represent modules and submodules.



\### 3.4 Activity and Completion Relationships



| Relationship | Cardinality |

|---|---|

| Learners to Activity Events | One-to-Many |

| Courses to Activity Events | One-to-Many |

| Enrollments to Activity Events | One-to-Many (optional) |

| Content Items to Activity Events | One-to-Many (optional) |

| Learners to Attempts | One-to-Many |

| Enrollments to Attempts | One-to-Many |

| Enrollments to Course Outcomes | One-to-Zero-or-One |

| Completion Rules to Course Outcomes | One-to-Many (optional) |



\### 3.5 Analytics and Monitoring Relationships



| Relationship | Cardinality |

|---|---|

| Learners to Weekly Engagement Metrics | One-to-Many |

| Courses to Weekly Engagement Metrics | One-to-Many |

| Cohorts to Cohort Metrics | One-to-Many |

| Courses to Cohort Metrics | One-to-Many |

| Users to Audit Logs | One-to-Many (optional) |



Anomaly records, ground truth and processing runs are maintained independently. They use entity identifiers and processing references rather than direct foreign keys to every affected business record.



\## 4. Simplified Relationship Diagram



```mermaid

erDiagram

&#x20;   USERS ||--o{ USER\_ROLES : assigned

&#x20;   ROLES ||--o{ USER\_ROLES : contains

&#x20;   ROLES ||--o{ ROLE\_PERMISSIONS : grants

&#x20;   PERMISSIONS ||--o{ ROLE\_PERMISSIONS : defines

&#x20;   USERS ||--o{ REFRESH\_TOKENS : owns

&#x20;   USERS ||--o| LEARNERS : linked\_to



&#x20;   LEARNERS ||--o{ ENROLLMENTS : creates

&#x20;   COURSES ||--o{ ENROLLMENTS : receives

&#x20;   COHORTS o|--o{ ENROLLMENTS : groups



&#x20;   LEARNERS ||--o{ COHORT\_LEARNERS : joins

&#x20;   COHORTS ||--o{ COHORT\_LEARNERS : contains

&#x20;   USERS ||--o{ INSTRUCTOR\_COURSES : assigned

&#x20;   COURSES ||--o{ INSTRUCTOR\_COURSES : taught



&#x20;   COURSES ||--o{ CONTENT\_ITEMS : contains

&#x20;   CONTENT\_ITEMS o|--o{ CONTENT\_ITEMS : parent\_of

&#x20;   COURSES ||--o{ ASSESSMENTS : defines

&#x20;   CONTENT\_ITEMS o|--o{ ASSESSMENTS : linked\_to



&#x20;   LEARNERS ||--o{ ACTIVITY\_EVENTS : generates

&#x20;   COURSES ||--o{ ACTIVITY\_EVENTS : records

&#x20;   ENROLLMENTS o|--o{ ACTIVITY\_EVENTS : relates

&#x20;   CONTENT\_ITEMS o|--o{ ACTIVITY\_EVENTS : relates



&#x20;   ASSESSMENTS ||--o{ ATTEMPTS : receives

&#x20;   LEARNERS ||--o{ ATTEMPTS : makes

&#x20;   ENROLLMENTS ||--o{ ATTEMPTS : contains



&#x20;   COURSES ||--o{ COMPLETION\_RULES : defines

&#x20;   ENROLLMENTS ||--o| COURSE\_OUTCOMES : produces

&#x20;   COMPLETION\_RULES o|--o{ COURSE\_OUTCOMES : evaluates



&#x20;   LEARNERS ||--o{ WEEKLY\_ENGAGEMENT\_METRICS : has

&#x20;   COURSES ||--o{ WEEKLY\_ENGAGEMENT\_METRICS : measures

&#x20;   COHORTS ||--o{ COHORT\_METRICS : has

&#x20;   COURSES ||--o{ COHORT\_METRICS : measures



&#x20;   USERS o|--o{ AUDIT\_LOGS : performs

```



Note: The diagram shows the main foreign-key relationships. Anomaly, ground-truth and processing tables are not connected by foreign keys in the current SQL schema.



\## 5. Primary Key and Foreign Key Design



\### Primary Keys



Primary keys uniquely identify records.



Examples:

\- learner\_id identifies each learner.

\- course\_id identifies each course.

\- enrollment\_id identifies each enrollment.

\- event\_id identifies each activity event.

\- assessment\_id identifies each assessment.

\- attempt\_id identifies each assessment attempt.



Some mapping tables use composite primary keys to prevent duplicate relationships.



\### Foreign Keys



Foreign keys maintain referential integrity between related tables.



Examples:

\- enrollments.learner\_id references learners.learner\_id.

\- enrollments.course\_id references courses.course\_id.

\- activity\_events.enrollment\_id references enrollments.enrollment\_id.

\- attempts.assessment\_id references assessments.assessment\_id.



\## 6. Important Database Design Decisions



\### 6.1 Historical Tracking



\- enrollment\_history stores enrollment status changes.

\- audit\_logs stores user actions and record changes.

\- refresh\_tokens stores token creation and revocation information.

\- activity\_events preserves individual activity records.



\### 6.2 Optional Relationships



Some relationships are optional in the current schema:



\- learners.user\_id can be NULL.

\- enrollments.cohort\_id can be NULL.

\- activity\_events.enrollment\_id can be NULL.

\- activity\_events.content\_item\_id can be NULL.

\- assessments.content\_item\_id can be NULL.

\- course\_outcomes.completion\_rule\_id can be NULL.

\- audit\_logs.user\_id can be NULL.



These optional fields support records that do not always have an associated parent record.



\### 6.3 Many-to-Many Relationships



Mapping tables are used to manage many-to-many relationships:



\- user\_roles connects users and roles.

\- role\_permissions connects roles and permissions.

\- cohort\_learners connects learners and cohorts.

\- instructor\_courses connects instructors and courses.



\### 6.4 Effective-Dated Rules



completion\_rules stores rule versions with effective\_from and effective\_to fields.



This supports different completion requirements over time.



\### 6.5 Anomaly and Ground Truth Separation



\- anomaly\_records stores detected anomalies.

\- ground\_truth stores expected anomaly labels.

\- Ground-truth information is kept separate from normal learning activity data.



\### 6.6 Processing Traceability



processing\_runs stores information about data processing operations, including execution status and record counts.



\## 7. Integrity Considerations



The database uses primary keys, foreign keys, unique constraints and check constraints.



However, some business relationships require additional application-level validation.



Examples:



1\. An activity event's learner and course must match its referenced enrollment.

2\. An attempt's learner must match its enrollment.

3\. An assessment and its linked content item must belong to the same course.

4\. An activity event's content item must belong to its referenced course.

5\. A course outcome must satisfy the applicable completion rule.

6\. Enrollment status transitions must follow the documented business rules.



These checks are handled by application-level business logic and validation processes because the current schema does not enforce all of them through foreign keys alone.



\## 8. Conclusion



The database provides a relational structure for managing users, roles, learners, courses, enrollments, assessments, activities, outcomes and analytics.



It also supports historical tracking, anomaly validation, processing traceability and role-based access control.



The structure is designed to maintain data integrity and support learning analytics across different learner groups and courses.
