# Learning Analytics Platform

## Demo Login Credentials

The following dedicated demo account is provided for project evaluation.

- **Dashboard URL:** http://localhost:8502
- **Email:** Keep your existing dummy reviewer email(vemulasaikrishna34@gmail.com).
- **Password:** Keep your existing dummy reviewer password(Saikrishna123@).

**Instructions:** Open the dashboard URL and log in using the demo credentials. After successful login, reviewers can explore the available analytics sections.

> These credentials are intended only for project demonstration and evaluation.

---

## 1. Project Overview

The Learning Analytics Platform is a three-tier application designed to analyze learner participation, course engagement, assessment progress, and learning outcomes.

The platform processes learner activity and assessment records to generate analytics, identify unusual activity, and evaluate learning progress across courses and cohorts.

The application uses synthetic data to simulate a large-scale learning environment.

## 2. Project Objectives

- Track learner participation and course engagement.
- Monitor assessment attempts and progress.
- Analyze course and cohort performance.
- Calculate and display course outcome information.
- Identify unusual or inconsistent activity records.
- Maintain data integrity and access control.
- Generate reproducible synthetic datasets.
- Provide analytics through an interactive dashboard.

## 3. Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | Streamlit, Plotly |
| Backend | Python, FastAPI |
| Database | MySQL 8 |
| ORM | SQLAlchemy |
| Authentication | JWT, Argon2 |
| Data Processing | Pandas, NumPy |
| Synthetic Data | Faker |
| Testing | Pytest, HTTPX |
| Deployment | Docker, Docker Compose |

## 4. System Architecture

The application follows a three-tier architecture.

### Tier 1 – Presentation Layer

Streamlit provides the user interface and interactive analytics dashboards.

### Tier 2 – Application Layer

FastAPI handles authentication, authorization, API requests, and analytics operations.

### Tier 3 – Database Layer

MySQL 8 stores user information, learner records, course details, activity events, assessments, and analytics-related information.

### Architecture Flow

```text
          Users
            |
            v
    Streamlit Dashboard
       Port 8502
            |
            v
       FastAPI
       Port 8000
            |
            v
  Authentication and RBAC
            |
            v
    Analytics and Business
          Logic
            |
            v
         MySQL 8
       Port 3306
```

## 5. User Roles and Access Control

The platform defines five user roles:

1. Platform Administrator
2. Academic Administrator
3. Instructor
4. Support Staff
5. Learner

Role-Based Access Control (RBAC) determines which operations users can perform.

Implemented access restrictions include:

- Instructors can access their assigned courses.
- Learners can access their own enrollment information.
- Administrative users receive access according to their assigned permissions.
- Backend permission checks protect restricted API endpoints.

## 6. Database Design

Database name: `learning_analytics`

The database contains 25 relational tables:

1. users
2. roles
3. permissions
4. user_roles
5. role_permissions
6. refresh_tokens
7. learners
8. courses
9. enrollments
10. cohorts
11. cohort_learners
12. content_items
13. activity_events
14. assessments
15. attempts
16. completion_rules
17. course_outcomes
18. enrollment_history
19. weekly_engagement_metrics
20. cohort_metrics
21. anomaly_records
22. ground_truth
23. processing_runs
24. audit_logs
25. instructor_courses

The database uses primary keys, foreign keys, and InnoDB tables to maintain relational integrity.

Refer to:

- `docs/entity_relationships.md`
- `docs/data_dictionary.md`
- `docs/schema_metadata.tsv`

## 7. Synthetic Data Generation

The platform uses a fixed random seed:

`20261022`

The generator supports large-scale synthetic data generation.

### Dataset Size

| Entity | Records |
|---|---:|
| Learners | 20,000 |
| Courses | 500 |
| Enrollments | 100,000 |
| Activity Events | 2,000,000 |
| Cohorts | 100 |
| Content Items | 4,000 |
| Assessments | 1,000 |
| Assessment Attempts | 116,820 |
| Ground Truth Labels | 20,000 |

### Data Generation Sequence

The generation process follows this order:

```cmd
python -m app.generation.master_data
python -m app.generation.dependent_master_data
python -m app.generation.enrollments
python -m app.generation.attempts
python -m app.generation.activity_events
```

Generated files are stored under:

```text
data/
    generated/
    ground_truth/
    manifests/
    processed/
```

### Controlled Anomaly Scenarios

Four anomaly categories are included:

1. Duplicate events that can inflate engagement.
2. Activity from learners who are not enrolled in the corresponding course.
3. Course completion recorded before a required assessment.
4. Timezone misalignment that can affect activity dates.

Ground-truth labels are maintained separately from activity records.

## 8. Authentication and Security

The authentication module provides:

- User registration.
- User login.
- JWT access tokens.
- Refresh token rotation.
- Logout and refresh token revocation.
- Protected user profile access.
- Argon2 password hashing.
- Permission-based authorization.

Public registration assigns the default Learner role.

Administrative access is protected through backend permission checks.

## 9. API Endpoints

### Authentication and Resources

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Application health check |
| POST | `/auth/register` | Register a learner |
| POST | `/auth/login` | Authenticate a user |
| POST | `/auth/refresh` | Refresh access credentials |
| POST | `/auth/logout` | Revoke refresh token |
| GET | `/auth/me` | Get current user profile |
| GET | `/admin/users` | Retrieve users with permission |
| GET | `/instructor/courses` | Retrieve assigned courses |
| GET | `/instructor/courses/{course_id}/enrollments` | Retrieve course enrollments |
| GET | `/learner/enrollments` | Retrieve own enrollments |

### Analytics

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/analytics/overview` | Overall platform metrics |
| GET | `/analytics/courses` | Course analytics |
| GET | `/analytics/assessments` | Assessment analytics |
| GET | `/analytics/engagement` | Learner engagement metrics |
| GET | `/analytics/cohorts` | Cohort analytics |
| GET | `/analytics/outcomes` | Course outcome information |
| GET | `/analytics/anomalies` | Anomaly summaries and evaluation |
| GET | `/analytics/processing-runs` | Processing run information |

Interactive API documentation:

`http://localhost:8000/docs`

## 10. Dashboard Sections

The Streamlit dashboard contains eight sections:

1. **Overview:** Displays overall learner and platform metrics.
2. **Courses:** Displays course-related analytics.
3. **Assessments:** Shows assessment attempts, scores, and pass rates.
4. **Engagement:** Displays learner activity and engagement information.
5. **Cohorts:** Provides cohort-level analytics.
6. **Outcomes:** Displays course outcome information.
7. **Anomalies:** Shows detected unusual activity records.
8. **Processing Runs:** Displays available processing run information.

The dashboard retrieves information through FastAPI rather than relying on hardcoded analytics values.

## 11. Data Validation and Anomaly Evaluation

The project includes validation scripts for checking generated data.

Validation areas include:

- Primary key uniqueness.
- Foreign key relationships.
- Valid entity references.
- Allowed event types and statuses.
- Timestamp ordering.
- Enrollment and assessment relationships.
- Attempt limits and score consistency.
- Anomaly labels and ground-truth relationships.
- Event ID uniqueness.

The implemented anomaly detection currently covers three categories:

- Duplicate events.
- Unenrolled activity.
- Premature course completion.

Timezone anomaly detection remains a limitation.

### Anomaly Evaluation Results

| Metric | Result |
|---|---:|
| True Positives | 15,000 |
| False Positives | 0 |
| False Negatives | 5,000 |
| Precision | 100% |
| Recall | 75% |
| F1 Score | 85.71% |

These results are based on the labelled anomaly cases in the generated ground-truth dataset, not a comprehensive evaluation of all normal records.

## 12. Local Setup

### Prerequisites

- Python 3.13
- MySQL 8
- pip
- Windows Command Prompt

### Step 1 – Create and activate virtual environment

```cmd
python -m venv .venv
.venv\Scripts\activate
```

### Step 2 – Install dependencies

```cmd
python -m pip install -r requirements.txt
```

### Step 3 – Configure environment variables

Create a `.env` file in the project root.

Configure:

```env
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=learning_analytics
DB_USER=your_mysql_username
DB_PASSWORD=your_mysql_password

SECRET_KEY=your_generated_secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
```

Use your own database credentials and a securely generated secret key.

Do not upload `.env` to GitHub.

### Step 4 – Create database schema

Execute the schema file using MySQL:

```cmd
"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p -e "CREATE DATABASE IF NOT EXISTS learning_analytics;"
```

Then:

```cmd
"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p learning_analytics < database\schema.sql
```

### Step 5 – Test database connection

```cmd
python -m scripts.test_db_connection
```

### Step 6 – Start FastAPI

```cmd
uvicorn app.main:app --reload
```

### Step 7 – Start Streamlit

Open another CMD window:

```cmd
cd /d learning-analytics-platform
.venv\Scripts\activate
streamlit run dashboard/app.py
```

The dashboard uses port 8501 by default in local development.

## 13. Docker Deployment

Docker and Docker Compose are configured for local deployment.

The application uses two containers:

- FastAPI container.
- Streamlit dashboard container.

The application connects to the existing MySQL 8 database running on the host machine.

### Build Docker Images

```cmd
docker compose build
```

### Start Containers

```cmd
docker compose up -d
```

### Check Running Containers

```cmd
docker compose ps
```

### View Logs

```cmd
docker compose logs --tail=50
```

### Stop Containers

```cmd
docker compose down
```

### Application URLs

| Component | URL |
|---|---|
| Dashboard | http://localhost:8502 |
| FastAPI | http://localhost:8000 |
| Swagger Documentation | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |

Before starting Docker, configure the `.env` file and ensure MySQL is running and accessible to Docker.

The Docker Compose configuration uses `host.docker.internal` to connect to the Windows MySQL host.

## 14. Testing

The project includes automated tests using Pytest and HTTPX.

Run:

```cmd
python -m pytest -v
```

Latest test execution:

- Total tests: 9
- Passed: 9
- Failed: 0

Additional test scripts are available in the `scripts` directory.

## 15. Project Structure

```text
learning-analytics-platform/
|
|-- app/
|   |-- api/
|   |   |-- routes/
|   |-- core/
|   |-- generation/
|   |-- models/
|   |-- rules/
|   |-- schemas/
|   |-- services/
|   |-- validation/
|
|-- dashboard/
|
|-- data/
|   |-- generated/
|   |-- ground_truth/
|   |-- manifests/
|   |-- processed/
|
|-- database/
|   |-- schema.sql
|
|-- docs/
|   |-- analytics_acceptance_tests.md
|   |-- business_rules.md
|   |-- data_dictionary.md
|   |-- entity_relationships.md
|   |-- metric_definitions.md
|   |-- schema_metadata.tsv
|
|-- migrations/
|-- scripts/
|-- tests/
|
|-- Dockerfile
|-- docker-compose.yml
|-- .dockerignore
|-- .env.example
|-- .gitignore
|-- requirements.txt
|-- README.md
```

## 16. Current Implementation Status

| Component | Status |
|---|---|
| Environment setup | Completed |
| MySQL database schema | Completed |
| SQLAlchemy connection | Tested |
| Authentication and JWT | Implemented and tested |
| RBAC and resource-level access | Implemented and tested |
| Synthetic data generation | Completed |
| Two million activity events | Generated and loaded |
| Ground-truth generation and loading | Completed |
| Data validation | Implemented |
| Three anomaly detection categories | Implemented |
| Analytics APIs | Implemented |
| Streamlit dashboard | Implemented |
| Automated tests | 9/9 passed |
| Docker deployment | Running and verified |
| Documentation | Prepared for review |
| GitHub publication | Final submission phase |

## 17. Known Limitations

The current implementation is a functional project demonstration. Some areas require further development before production deployment.

- Timezone anomaly detection is not implemented.
- Content completion percentage is not calculated.
- The fast outcome processor does not currently determine completed or failed outcomes.
- Engagement percentage in the fast outcome processor is not calculated.
- Processing run records are not yet populated.
- Additional production security controls, including login rate limiting and account lockout, require further work.
- The anomaly evaluation uses labelled positive cases and does not measure false positives against the full normal dataset.

## 18. Reproducibility

Synthetic data generation uses a fixed random seed (`20261022`).

Generation manifests record dataset information, seeds, record counts, and checksums.

The generated datasets can be used for repeatable testing and analytics evaluation.

## 19. Documentation References

Additional project documentation:

- `docs/business_rules.md`
- `docs/metric_definitions.md`
- `docs/entity_relationships.md`
- `docs/data_dictionary.md`
- `docs/analytics_acceptance_tests.md`
- `docs/schema_metadata.tsv`

---

**Project:** Learning Analytics Platform
**Architecture:** Three-tier application
**Frontend:** Streamlit
**Backend:** FastAPI
**Database:** MySQL 8
**Deployment:** Docker Compose
