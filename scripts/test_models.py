
from sqlalchemy import inspect

from app.core.database import engine
from app.models.user import (
    User,
    Role,
    Permission,
    UserRole,
    RolePermission,
)


def test_model_mapping():
    expected_tables = [
        "users",
        "roles",
        "permissions",
        "user_roles",
        "role_permissions",
    ]

    inspector = inspect(engine)
    database_tables = inspector.get_table_names()

    for table in expected_tables:
        assert table in database_tables, f"Missing table: {table}"

    print("SQLAlchemy model mapping successful!")

    for model in [User, Role, Permission, UserRole, RolePermission]:
        print(f"{model.__name__}: {model.__tablename__}")


if __name__ == "__main__":
    test_model_mapping()
