from getpass import getpass

from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import hash_password

db = SessionLocal()

try:
    user = db.query(User).filter(
        User.username == "platform_admin"
    ).one_or_none()

    if not user:
        print("Administrator account not found.")
    elif user.account_status != "ACTIVE":
        print("Account is not active.")
    else:
        password = getpass("Enter new password (hidden): ")
        confirm = getpass("Confirm new password (hidden): ")

        if len(password) < 12:
            print("Password must contain at least 12 characters.")
        elif password != confirm:
            print("Passwords do not match.")
        else:
            user.password_hash = hash_password(password)
            db.commit()
            print("Administrator password reset successfully.")

finally:
    db.close()