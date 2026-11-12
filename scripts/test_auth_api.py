
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.core.database import SessionLocal
from app.models.user import User, Role, UserRole
from app.models.refresh_token import RefreshToken


client = TestClient(app)


def test_authentication_workflow():
    unique_id = uuid4().hex[:10]

    username = f"testuser_{unique_id}"
    email = f"test_{unique_id}@example.com"
    password = "TestPassword@12345"

    # 1. Register user
    response = client.post(
        "/auth/register",
        json={
            "username": username,
            "email": email,
            "full_name": "Test Learner",
            "password": password,
        },
    )

    assert response.status_code == 201, response.text

    user_data = response.json()
    user_id = user_data["user_id"]

    print("User registration: PASSED")

    # 2. Verify database record and password hashing
    db = SessionLocal()

    try:
        user = db.get(User, user_id)

        assert user is not None
        assert user.password_hash != password
        assert user.password_hash.startswith("$argon2")

        role = db.scalar(
            select(Role)
            .join(UserRole)
            .where(UserRole.user_id == user_id)
        )

        assert role is not None
        assert role.role_code == "LEARNER"

        print("Password hashing in MySQL: PASSED")
        print("Default learner role assignment: PASSED")

    finally:
        db.close()

    # 3. Login
    response = client.post(
        "/auth/login",
        json={
            "username_or_email": username,
            "password": password,
        },
    )

    assert response.status_code == 200, response.text

    tokens = response.json()
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    print("Login: PASSED")

    # 4. Access protected profile
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["user_id"] == user_id

    print("Protected profile access: PASSED")

    # 5. Reject unauthenticated access
    response = client.get("/auth/me")

    assert response.status_code == 401

    print("Unauthenticated access rejection: PASSED")

    # 6. Refresh token rotation
    response = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200, response.text

    new_tokens = response.json()
    new_refresh_token = new_tokens["refresh_token"]

    assert new_refresh_token != refresh_token

    print("Refresh token rotation: PASSED")

    # 7. Reject reuse of old refresh token
    response = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 401

    print("Old refresh token reuse rejection: PASSED")

    # 8. Logout and revoke current refresh token
    response = client.post(
        "/auth/logout",
        json={"refresh_token": new_refresh_token},
        headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
    )

    assert response.status_code == 200

    print("Logout: PASSED")

    # 9. Verify revoked token cannot be reused
    response = client.post(
        "/auth/refresh",
        json={"refresh_token": new_refresh_token},
    )

    assert response.status_code == 401

    print("Revoked refresh token rejection: PASSED")

    # 10. Verify refresh token records exist
    db = SessionLocal()

    try:
        records = db.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id
            )
        ).all()

        assert len(records) >= 2
        assert all(
            len(record.token_hash) == 64
            for record in records
        )

        print("Refresh token hash persistence: PASSED")

    finally:
        db.close()

    print("\nALL AUTHENTICATION TESTS PASSED!")


if __name__ == "__main__":
    test_authentication_workflow()
