import hashlib
import os
import re
from database import create_user, get_user_by_email


def hash_password(password: str) -> str:
    salt = os.environ.get("SECRET_KEY", "tradescope_salt")
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed


def validate_email(email: str) -> bool:
    return bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email))


def register(email: str, password: str) -> dict:
    email = email.strip().lower()
    if not validate_email(email):
        return {"ok": False, "error": "Email格式不正確"}
    if len(password) < 6:
        return {"ok": False, "error": "密碼至少6個字元"}
    if get_user_by_email(email):
        return {"ok": False, "error": "此Email已被註冊"}
    user_id = create_user(email, hash_password(password))
    return {"ok": True, "user_id": user_id, "email": email}


def login(email: str, password: str) -> dict:
    email = email.strip().lower()
    user = get_user_by_email(email)
    if not user:
        return {"ok": False, "error": "Email或密碼錯誤"}
    if not verify_password(password, user["password"]):
        return {"ok": False, "error": "Email或密碼錯誤"}
    return {"ok": True, "user_id": user["id"], "email": user["email"]}
