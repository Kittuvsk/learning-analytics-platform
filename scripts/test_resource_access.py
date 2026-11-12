
from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.main import app
from app.core.database import SessionLocal
from app.models.user import User, Role, UserRole

client = TestClient(app)


def register_user(prefix):
    unique = uuid4().hex[:8]
    username = f"{prefix}_{unique}"
    email = f"{prefix}_{unique}@example.com"
    password = "TestPassword@12345"

    response = client.post(
        "/auth/register",
        json={
            "username": username,
            "email": email,
            "full_name": f"Test {prefix.title()}",
            "password": password,
        },
    )

    assert response.status_code == 201, response.text

    response = client.post(
        "/auth/login",
        json={
            "username_or_email": username,
            "password": password,
        },
    )

    assert response.status_code == 200, response.text

    return response.json()["access_token"], username


def assign_role(db, username, role_code):
    user = db.scalar(
        select(User).where(User.username == username)
    )

    role = db.scalar(
        select(Role).where(Role.role_code == role_code)
    )

    learner_role = db.scalar(
        select(Role).where(Role.role_code == "LEARNER")
    )

    assert user is not None
    assert role is not None
    assert learner_role is not None

    # Keep the existing learner role when the target is LEARNER.
    if role_code == "LEARNER":
        existing = db.get(
            UserRole,
            (user.user_id, role.role_id),
        )

        if existing is None:
            db.add(
                UserRole(
                    user_id=user.user_id,
                    role_id=role.role_id,
                )
            )

    else:
        # Remove the default learner role before assigning
        # another role, such as INSTRUCTOR.
        existing_learner = db.get(
            UserRole,
            (user.user_id, learner_role.role_id),
        )

        if existing_learner is not None:
            db.delete(existing_learner)

        existing_target = db.get(
            UserRole,
            (user.user_id, role.role_id),
        )

        if existing_target is None:
            db.add(
                UserRole(
                    user_id=user.user_id,
                    role_id=role.role_id,
                )
            )

    db.flush()

    return user.user_id

def test_resource_access():
    unique = uuid4().hex[:8]

    # Create two instructors and two learners.
    instructor_a_token, instructor_a_name = register_user("instructor_a")
    instructor_b_token, instructor_b_name = register_user("instructor_b")

    learner_a_token, learner_a_name = register_user("learner_a")
    learner_b_token, learner_b_name = register_user("learner_b")

    course_a = f"CRS-A-{unique}"
    course_b = f"CRS-B-{unique}"

    learner_a_id = f"LRNA-{unique}"
    learner_b_id = f"LRNB-{unique}"

    enrollment_a = f"ENR-{learner_a_id}-{course_a}"
    enrollment_b = f"ENR-{learner_b_id}-{course_b}"

    db = SessionLocal()

    try:
        instructor_a_id = assign_role(
            db, instructor_a_name, "INSTRUCTOR"
        )

        instructor_b_id = assign_role(
            db, instructor_b_name, "INSTRUCTOR"
        )

        learner_a_user_id = assign_role(
            db, learner_a_name, "LEARNER"
        )

        learner_b_user_id = assign_role(
            db, learner_b_name, "LEARNER"
        )

        # Create two courses.
        db.execute(
            text("""
                INSERT INTO courses
                    (course_id, course_name, course_status)
                VALUES
                    (:course_a, 'Resource Test Course A', 'PUBLISHED'),
                    (:course_b, 'Resource Test Course B', 'PUBLISHED')
            """),
            {
                "course_a": course_a,
                "course_b": course_b,
            },
        )

        # Assign one course to each instructor.
        db.execute(
            text("""
                INSERT INTO instructor_courses
                    (instructor_user_id, course_id)
                VALUES
                    (:instructor_a, :course_a),
                    (:instructor_b, :course_b)
            """),
            {
                "instructor_a": instructor_a_id,
                "instructor_b": instructor_b_id,
                "course_a": course_a,
                "course_b": course_b,
            },
        )

        # Link application users to learner records.
        db.execute(
            text("""
                INSERT INTO learners
                    (learner_id, user_id, first_name, last_name,
                     email, registration_date)
                VALUES
                    (:learner_a, :user_a, 'Learner', 'A',
                     :email_a, CURDATE()),
                    (:learner_b, :user_b, 'Learner', 'B',
                     :email_b, CURDATE())
            """),
            {
                "learner_a": learner_a_id,
                "learner_b": learner_b_id,
                "user_a": learner_a_user_id,
                "user_b": learner_b_user_id,
                "email_a": f"{learner_a_id}@example.com",
                "email_b": f"{learner_b_id}@example.com",
            },
        )

        # Create one enrollment in each course.
        db.execute(
            text("""
                INSERT INTO enrollments
                    (enrollment_id, learner_id, course_id,
                     enrollment_status, enrolled_at)
                VALUES
                    (:enrollment_a, :learner_a, :course_a,
                     'ENROLLED', :now),
                    (:enrollment_b, :learner_b, :course_b,
                     'ENROLLED', :now)
            """),
            {
                "enrollment_a": enrollment_a,
                "enrollment_b": enrollment_b,
                "learner_a": learner_a_id,
                "learner_b": learner_b_id,
                "course_a": course_a,
                "course_b": course_b,
                "now": datetime.utcnow(),
            },
        )

        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()

    # Test 1: Instructor A sees only Course A.
    response = client.get(
        "/instructor/courses",
        headers={
            "Authorization": f"Bearer {instructor_a_token}"
        },
    )

    assert response.status_code == 200, response.text

    course_ids = {
        item["course_id"] for item in response.json()
    }

    assert course_a in course_ids
    assert course_b not in course_ids

    print("Instructor course isolation: PASSED")

    # Test 2: Instructor A sees only Course A enrollments.
    response = client.get(
        f"/instructor/courses/{course_a}/enrollments",
        headers={
            "Authorization": f"Bearer {instructor_a_token}"
        },
    )

    assert response.status_code == 200, response.text

    enrollment_ids = {
        item["enrollment_id"] for item in response.json()
    }

    assert enrollment_a in enrollment_ids
    assert enrollment_b not in enrollment_ids

    print("Instructor enrollment isolation: PASSED")

    # Test 3: Instructor A cannot access Course B.
    response = client.get(
        f"/instructor/courses/{course_b}/enrollments",
        headers={
            "Authorization": f"Bearer {instructor_a_token}"
        },
    )

    assert response.status_code == 404

    print("Unassigned course access rejection: PASSED")

    # Test 4: Learner A sees only their own enrollment.
    response = client.get(
        "/learner/enrollments",
        headers={
            "Authorization": f"Bearer {learner_a_token}"
        },
    )

    assert response.status_code == 200, response.text

    enrollment_ids = {
        item["enrollment_id"] for item in response.json()
    }

    assert enrollment_a in enrollment_ids
    assert enrollment_b not in enrollment_ids

    print("Learner enrollment isolation: PASSED")

    # Test 5: Learner B sees only their own enrollment.
    response = client.get(
        "/learner/enrollments",
        headers={
            "Authorization": f"Bearer {learner_b_token}"
        },
    )

    assert response.status_code == 200, response.text

    enrollment_ids = {
        item["enrollment_id"] for item in response.json()
    }

    assert enrollment_b in enrollment_ids
    assert enrollment_a not in enrollment_ids

    print("Cross-learner data isolation: PASSED")

    print("\nALL RESOURCE ACCESS TESTS PASSED!")


if __name__ == "__main__":
    test_resource_access()
