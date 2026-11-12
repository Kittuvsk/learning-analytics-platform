
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.routes.auth import get_db, get_current_user
from app.models.user import User


router = APIRouter(
    prefix="/analytics",
    tags=["Extended Analytics"],
)


def get_analytics_scope(db: Session, user: User):
    permission_query = text("""
        SELECT DISTINCT p.permission_code
        FROM user_roles ur
        JOIN roles r ON r.role_id = ur.role_id
        JOIN role_permissions rp ON rp.role_id = r.role_id
        JOIN permissions p ON p.permission_id = rp.permission_id
        WHERE ur.user_id = :user_id
          AND p.permission_code IN (
              'ANALYTICS_READ_ALL',
              'ANALYTICS_READ_ASSIGNED'
          )
    """)

    permissions = set(
        db.execute(
            permission_query,
            {"user_id": user.user_id},
        ).scalars().all()
    )

    if "ANALYTICS_READ_ALL" in permissions:
        return "ALL", ""

    if "ANALYTICS_READ_ASSIGNED" in permissions:
        return (
            "ASSIGNED_COURSES",
            """
            AND EXISTS (
                SELECT 1
                FROM instructor_courses ic
                WHERE ic.course_id = {alias}.course_id
                  AND ic.instructor_user_id = :user_id
            )
            """,
        )

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Analytics permission required",
    )


def to_int(value):
    return int(value or 0)


def to_float(value, digits=2):
    return round(float(value), digits) if value is not None else 0.0


@router.get("/engagement")
def get_engagement_analytics(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scope, filter_template = get_analytics_scope(db, current_user)
    course_filter = filter_template.format(alias="e")

    start_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)

    query = text(f"""
        WITH ranked_events AS (
            SELECT
                e.event_id,
                e.learner_id,
                e.course_id,
                e.content_item_id,
                e.event_type,
                e.event_time_utc,
                e.duration_seconds,
                ROW_NUMBER() OVER (
                    PARTITION BY
                        CASE
                            WHEN e.source_event_id IS NULL
                            THEN CONCAT('EVENT:', e.event_id)
                            ELSE CONCAT('SOURCE:', e.source_event_id)
                        END
                    ORDER BY e.received_at_utc, e.event_id
                ) AS duplicate_rank
            FROM activity_events e
            JOIN enrollments en
                ON en.enrollment_id = e.enrollment_id
               AND en.learner_id = e.learner_id
               AND en.course_id = e.course_id
            WHERE e.event_time_utc >= :start_time
              AND e.event_time_utc <= UTC_TIMESTAMP()
              AND (
                  en.enrollment_status <> 'WITHDRAWN'
                  OR en.withdrawn_at IS NULL
                  OR e.event_time_utc <= en.withdrawn_at
              )
              {course_filter}
        ),
        valid_events AS (
            SELECT *
            FROM ranked_events
            WHERE duplicate_rank = 1
        )
        SELECT
            COUNT(*) AS valid_event_count,
            COUNT(DISTINCT learner_id) AS active_learners,
            COUNT(DISTINCT course_id) AS active_courses,
            COUNT(DISTINCT DATE(event_time_utc)) AS active_days,
            COUNT(DISTINCT content_item_id) AS unique_content_items,
            ROUND(SUM(duration_seconds) / 60.0, 2)
                AS total_engagement_minutes,
            SUM(event_type = 'COURSE_COMPLETED')
                AS course_completion_events,
            SUM(event_type = 'VIDEO_COMPLETED')
                AS video_completion_events,
            SUM(event_type = 'QUIZ_SUBMITTED')
                AS quiz_submission_events
        FROM valid_events
    """)

    result = db.execute(
        query,
        {
            "user_id": current_user.user_id,
            "start_time": start_time,
        },
    ).mappings().one()

    return {
        "scope": scope,
        "period_days": days,
        "start_time_utc": start_time.isoformat(),
        "metrics": {
            "valid_event_count": to_int(result["valid_event_count"]),
            "active_learners": to_int(result["active_learners"]),
            "active_courses": to_int(result["active_courses"]),
            "active_days": to_int(result["active_days"]),
            "unique_content_items": to_int(result["unique_content_items"]),
            "total_engagement_minutes": to_float(
                result["total_engagement_minutes"]
            ),
            "course_completion_events": to_int(
                result["course_completion_events"]
            ),
            "video_completion_events": to_int(
                result["video_completion_events"]
            ),
            "quiz_submission_events": to_int(
                result["quiz_submission_events"]
            ),
        },
    }


@router.get("/cohorts")
def get_cohort_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scope, filter_template = get_analytics_scope(db, current_user)
    course_filter = filter_template.format(alias="e")

    query = text(f"""
        SELECT
            c.cohort_id,
            c.cohort_code,
            c.cohort_name,
            c.cohort_status,
            c.start_date,
            c.end_date,

            COUNT(DISTINCT e.enrollment_id) AS enrolled_count,

            COUNT(DISTINCT CASE
                WHEN e.enrollment_status IN ('ENROLLED', 'IN_PROGRESS')
                THEN e.enrollment_id
            END) AS active_count,

            COUNT(DISTINCT CASE
                WHEN o.outcome_status = 'COMPLETED'
                THEN e.enrollment_id
            END) AS completed_count,

            COUNT(DISTINCT CASE
                WHEN o.outcome_status = 'FAILED'
                THEN e.enrollment_id
            END) AS failed_count,

            ROUND(
                100.0 * COUNT(DISTINCT CASE
                    WHEN o.outcome_status = 'COMPLETED'
                    THEN e.enrollment_id
                END) / NULLIF(COUNT(DISTINCT e.enrollment_id), 0),
                2
            ) AS completion_rate

        FROM cohorts c
        LEFT JOIN enrollments e
            ON e.cohort_id = c.cohort_id
        LEFT JOIN course_outcomes o
            ON o.enrollment_id = e.enrollment_id
        WHERE 1 = 1
        {course_filter}
        GROUP BY
            c.cohort_id,
            c.cohort_code,
            c.cohort_name,
            c.cohort_status,
            c.start_date,
            c.end_date
        ORDER BY c.start_date DESC
    """)

    rows = db.execute(
        query,
        {"user_id": current_user.user_id},
    ).mappings().all()

    cohorts = [
        {
            "cohort_id": row["cohort_id"],
            "cohort_code": row["cohort_code"],
            "cohort_name": row["cohort_name"],
            "cohort_status": row["cohort_status"],
            "start_date": str(row["start_date"]),
            "end_date": (
                str(row["end_date"]) if row["end_date"] else None
            ),
            "enrolled_count": to_int(row["enrolled_count"]),
            "active_count": to_int(row["active_count"]),
            "completed_count": to_int(row["completed_count"]),
            "failed_count": to_int(row["failed_count"]),
            "completion_rate_percent": to_float(
                row["completion_rate"]
            ),
        }
        for row in rows
    ]

    return {
        "scope": scope,
        "total_cohorts": len(cohorts),
        "cohorts": cohorts,
    }


@router.get("/outcomes")
def get_course_outcomes(
    limit: int = Query(default=100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scope, filter_template = get_analytics_scope(db, current_user)

    if scope == "ALL":
        course_filter = ""
    else:
        course_filter = """
            AND EXISTS (
                SELECT 1
                FROM enrollments en
                JOIN instructor_courses ic
                    ON ic.course_id = en.course_id
                WHERE en.enrollment_id = o.enrollment_id
                  AND ic.instructor_user_id = :user_id
            )
        """

    summary_query = text(f"""
        SELECT
            COUNT(*) AS total_outcomes,

            SUM(o.outcome_status = 'COMPLETED')
                AS completed,

            SUM(o.outcome_status = 'IN_PROGRESS')
                AS in_progress,

            SUM(o.outcome_status = 'NOT_STARTED')
                AS not_started,

            SUM(o.outcome_status = 'FAILED')
                AS failed,

            SUM(o.outcome_status = 'WITHDRAWN')
                AS withdrawn,

            SUM(o.outcome_status = 'SUSPENDED')
                AS suspended,

            AVG(o.content_completion_percentage)
                AS average_content_completion,

            AVG(o.assessment_completion_percentage)
                AS average_assessment_completion,

            AVG(o.final_assessment_score)
                AS average_final_score

        FROM course_outcomes o
        WHERE 1 = 1
        {course_filter}
    """)

    detail_query = text(f"""
        SELECT
            o.outcome_id,
            o.enrollment_id,
            en.learner_id,
            en.course_id,
            o.content_completion_percentage,
            o.assessment_completion_percentage,
            o.final_assessment_score,
            o.outcome_status,
            o.calculated_at,
            o.completion_reason
        FROM course_outcomes o
        JOIN enrollments en
            ON en.enrollment_id = o.enrollment_id
        WHERE 1 = 1
        {course_filter}
        ORDER BY o.calculated_at DESC
        LIMIT :limit
    """)

    params = {
        "user_id": current_user.user_id,
        "limit": limit,
    }

    summary = db.execute(
        summary_query,
        params,
    ).mappings().one()

    rows = db.execute(
        detail_query,
        params,
    ).mappings().all()

    total = to_int(summary["total_outcomes"])
    completed = to_int(summary["completed"])

    return {
        "scope": scope,
        "summary": {
            "total_outcomes": total,
            "completed": completed,
            "in_progress": to_int(summary["in_progress"]),
            "not_started": to_int(summary["not_started"]),
            "failed": to_int(summary["failed"]),
            "withdrawn": to_int(summary["withdrawn"]),
            "suspended": to_int(summary["suspended"]),
            "completion_rate_percent": (
                round(completed / total * 100, 2) if total else 0.0
            ),
            "average_content_completion_percent": (
                to_float(summary["average_content_completion"])
                if summary["average_content_completion"] is not None
                else None
            ),
            "average_assessment_completion_percent": to_float(
                summary["average_assessment_completion"]
            ),
            "average_final_score": (
                to_float(summary["average_final_score"])
                if summary["average_final_score"] is not None
                else None
            ),
        },
        "records_returned": len(rows),
        "records": [
            {
                "outcome_id": row["outcome_id"],
                "enrollment_id": row["enrollment_id"],
                "learner_id": row["learner_id"],
                "course_id": row["course_id"],
                "content_completion_percentage": (
                    to_float(row["content_completion_percentage"])
                    if row["content_completion_percentage"] is not None
                    else None
                ),
                "assessment_completion_percentage": to_float(
                    row["assessment_completion_percentage"]
                ),
                "final_assessment_score": (
                    to_float(row["final_assessment_score"])
                    if row["final_assessment_score"] is not None
                    else None
                ),
                "outcome_status": row["outcome_status"],
                "calculated_at": row["calculated_at"].isoformat(),
                "completion_reason": row["completion_reason"],
            }
            for row in rows
        ],
    }


@router.get("/anomalies")
def get_anomaly_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scope, filter_template = get_analytics_scope(db, current_user)

    if scope == "ALL":
        anomaly_filter = ""
        truth_filter = ""
    else:
        anomaly_filter = """
            AND (
                a.entity_type = 'ACTIVITY_EVENT'
                AND EXISTS (
                    SELECT 1
                    FROM activity_events ae
                    JOIN instructor_courses ic
                        ON ic.course_id = ae.course_id
                    WHERE ae.event_id = a.entity_id
                      AND ic.instructor_user_id = :user_id
                )
            )
        """
        truth_filter = """
            AND (
                gt.entity_type = 'ACTIVITY_EVENT'
                AND EXISTS (
                    SELECT 1
                    FROM activity_events ae
                    JOIN instructor_courses ic
                        ON ic.course_id = ae.course_id
                    WHERE ae.event_id = gt.entity_id
                      AND ic.instructor_user_id = :user_id
                )
            )
        """

    summary_query = text(f"""
        SELECT
            COUNT(*) AS total_detected,

            SUM(a.detection_status = 'OPEN') AS open_count,
            SUM(a.detection_status = 'REVIEWED') AS reviewed_count,
            SUM(a.detection_status = 'RESOLVED') AS resolved_count,
            SUM(a.detection_status = 'FALSE_POSITIVE')
                AS false_positive_count,

            SUM(a.severity = 'LOW') AS low_count,
            SUM(a.severity = 'MEDIUM') AS medium_count,
            SUM(a.severity = 'HIGH') AS high_count,
            SUM(a.severity = 'CRITICAL') AS critical_count

        FROM anomaly_records a
        WHERE 1 = 1
        {anomaly_filter}
    """)

    issue_query = text(f"""
        SELECT
            a.issue_type,
            COUNT(*) AS issue_count
        FROM anomaly_records a
        WHERE 1 = 1
        {anomaly_filter}
        GROUP BY a.issue_type
        ORDER BY issue_count DESC
    """)

    evaluation_query = text(f"""
        SELECT
            COUNT(*) AS actual_positive_count,

            SUM(CASE
                WHEN EXISTS (
                    SELECT 1
                    FROM anomaly_records a
                    WHERE a.issue_type = gt.issue_type
                      AND a.entity_type = gt.entity_type
                      AND a.entity_id = gt.entity_id
                )
                THEN 1 ELSE 0
            END) AS true_positive_count

        FROM ground_truth gt
        WHERE gt.expected_label = 1
        {truth_filter}
    """)

    params = {"user_id": current_user.user_id}

    summary = db.execute(
        summary_query, params
    ).mappings().one()

    issue_rows = db.execute(
        issue_query, params
    ).mappings().all()

    evaluation = db.execute(
        evaluation_query, params
    ).mappings().one()

    detected = to_int(summary["total_detected"])
    actual_positive = to_int(evaluation["actual_positive_count"])
    true_positive = to_int(evaluation["true_positive_count"])

    precision = true_positive / detected if detected else 0.0
    recall = (
        true_positive / actual_positive if actual_positive else 0.0
    )
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )

    return {
        "scope": scope,
        "summary": {
            "total_detected": detected,
            "open": to_int(summary["open_count"]),
            "reviewed": to_int(summary["reviewed_count"]),
            "resolved": to_int(summary["resolved_count"]),
            "marked_false_positive": to_int(
                summary["false_positive_count"]
            ),
            "low_severity": to_int(summary["low_count"]),
            "medium_severity": to_int(summary["medium_count"]),
            "high_severity": to_int(summary["high_count"]),
            "critical_severity": to_int(summary["critical_count"]),
        },
        "by_issue_type": [
            {
                "issue_type": row["issue_type"],
                "count": to_int(row["issue_count"]),
            }
            for row in issue_rows
        ],
        "evaluation": {
            "ground_truth_positive": actual_positive,
            "true_positives": true_positive,
            "precision_percent": round(precision * 100, 2),
            "recall_percent": round(recall * 100, 2),
            "f1_score": round(f1, 4),
            "note": (
                "Evaluation compares detected anomaly records with "
                "positive ground-truth labels. Run anomaly detection "
                "before interpreting these metrics."
            ),
        },
    }


@router.get("/processing-runs")
def get_processing_runs(
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scope, _ = get_analytics_scope(db, current_user)
    if scope != "ALL":
        raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Platform administrator permission required",
        )


    query = text("""
        SELECT
            processing_run_id,
            run_code,
            process_type,
            run_status,
            started_at,
            finished_at,
            input_record_count,
            output_record_count,
            error_record_count,
            error_summary
        FROM processing_runs
        ORDER BY started_at DESC
        LIMIT :limit
    """)

    rows = db.execute(
        query,
        {"limit": limit},
    ).mappings().all()

    return {
        "scope": scope,
        "total_runs_returned": len(rows),
        "runs": [
            {
                "processing_run_id": row["processing_run_id"],
                "run_code": row["run_code"],
                "process_type": row["process_type"],
                "run_status": row["run_status"],
                "started_at": row["started_at"].isoformat(),
                "finished_at": (
                    row["finished_at"].isoformat()
                    if row["finished_at"]
                    else None
                ),
                "input_record_count": to_int(
                    row["input_record_count"]
                ),
                "output_record_count": to_int(
                    row["output_record_count"]
                ),
                "error_record_count": to_int(
                    row["error_record_count"]
                ),
                "error_summary": row["error_summary"],
            }
            for row in rows
        ],
    }
