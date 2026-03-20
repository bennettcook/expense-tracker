from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field
import bcrypt
from jose import JWTError, jwt
import os

from database import get_connection

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

SECRET_KEY = os.getenv("JWT_SECRET", "change-me-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24


class UserCredentials(BaseModel):
    email: str = Field(..., min_length=3, max_length=254)
    password: str = Field(..., min_length=8)


class Token(BaseModel):
    access_token: str
    token_type: str


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_token(user_id: int, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    payload = {"sub": str(user_id), "email": email, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=401,
        detail="Invalid or expired session. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        email = payload.get("email")
        if user_id is None:
            raise credentials_exception
        return {"id": int(user_id), "email": email}
    except JWTError:
        raise credentials_exception


@router.post("/register", response_model=Token, status_code=201)
def register(credentials: UserCredentials):
    cur = None
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE email = %s", (credentials.email,))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="An account with that email already exists.")
        hashed = hash_password(credentials.password)
        cur.execute(
            "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id",
            (credentials.email, hashed),
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        return {"access_token": create_token(user_id, credentials.email), "token_type": "bearer"}
    finally:
        if cur:
            cur.close()
        conn.close()


@router.post("/login", response_model=Token)
def login(credentials: UserCredentials):
    cur = None
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, password_hash FROM users WHERE email = %s", (credentials.email,)
        )
        row = cur.fetchone()
        # Use constant-time comparison even on missing user to avoid timing attacks
        dummy_hash = "$2b$12$invalidhashpadding000000000000000000000000000000000000"
        stored_hash = row[1] if row else dummy_hash
        password_ok = verify_password(credentials.password, stored_hash)
        if not row or not password_ok:
            raise HTTPException(status_code=401, detail="Incorrect email or password.")
        return {"access_token": create_token(row[0], credentials.email), "token_type": "bearer"}
    finally:
        if cur:
            cur.close()
        conn.close()
