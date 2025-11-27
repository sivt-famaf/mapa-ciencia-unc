import os
import hmac
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt, JWTError

USERNAME = os.getenv("BASIC_AUTH_USERNAME")
PASSWORD = os.getenv("BASIC_AUTH_PASSWORD")
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60

if not USERNAME or not PASSWORD or not JWT_SECRET:
    raise RuntimeError(
        "Environment vars BASIC_AUTH_USERNAME/PASSWORD/JWT_SECRET not set."
    )

USERS = {
    USERNAME: {
        "password": PASSWORD,
        "privileged": True,
    }
}


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def create_jwt_token(username: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)

    payload = {
        "sub": username,
        "exp": expire,
    }

    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_jwt_token(token: str) -> str:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None or username not in USERS:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return username

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def login(form: OAuth2PasswordRequestForm = Depends()):
    username = form.username
    password = form.password

    stored = USERS.get(username)
    if not stored or not hmac.compare_digest(password, stored["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    access_token = create_jwt_token(username)
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


def require_auth(token: str = Depends(oauth2_scheme)):
    username = verify_jwt_token(token)
    return username
