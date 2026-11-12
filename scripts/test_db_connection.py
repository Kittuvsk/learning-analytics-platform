
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import engine


def test_database_connection():
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT VERSION(), DATABASE()")
            )

            version, database = result.fetchone()

            print("Database connection successful!")
            print("MySQL Version:", version)
            print("Connected Database:", database)

    except SQLAlchemyError as error:
        print("Database connection failed!")
        print("Error:", error)
        raise


if __name__ == "__main__":
    test_database_connection()
