
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.core.database import SessionLocal
from app.models.user import User, Role, UserRole

client = TestClient(app)


def register_and_login(username, email):
    password = "TestPassword@12345"

    response = client.post(
        "/auth/register",
        json={
            "username": username,
            "email": email,
            "full_name": "RBAC Test User",
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

    return response.json()["access_token"]


def test_rbac():
    unique_id = uuid4().hex[:10]

    learner_token = register_and_login(
        f"learner_{unique_id}",
        f"learner_{unique_id}@example.com",
    )

    admin_token = register_and_login(
        f"admin_{unique_id}",
        f"admin_{unique_id}@example.com",
    )

    # Promote only the dedicated test account.
    db = SessionLocal()

    try:
        admin_user = db.scalar(
            select(User).where(
                User.username == f"admin_{unique_id}"
            )
        )

        learner_role = db.scalar(
            select(Role).where(
                Role.role_code == "LEARNER"
            )
        )

        admin_role = db.scalar(
            select(Role).where(
                Role.role_code == "PLATFORM_ADMIN"
            )
        )

        assert admin_user is not None
        assert learner_role is not None
        assert admin_role is not None

        existing_assignment = db.get(
            UserRole,
            (admin_user.user_id, learner_role.role_id),
        )

        if existing_assignment:
            db.delete(existing_assignment)

        db.add(
            UserRole(
                user_id=admin_user.user_id,
                role_id=admin_role.role_id,
            )
        )

        db.commit()

    finally:
        db.close()

    # Test 1: Learner must be denied.
    response = client.get(
        "/admin/users",
        headers={
            "Authorization": f"Bearer {learner_token}"
        },
    )

    print("Learner response status:", response.status_code)
    print("Learner response body:", response.text)

    assert response.status_code == 403, response.text

    print("Learner administrator-access rejection: PASSED")

    # Test 2: Administrator must be allowed.
    response = client.get(
        "/admin/users",
        headers={
            "Authorization": f"Bearer {admin_token}"
        },
    )

    assert response.status_code == 200, response.text

    print("Platform administrator access: PASSED")
    print("\nALL RBAC TESTS PASSED!")


if __name__ == "__main__":
    test_rbac()
