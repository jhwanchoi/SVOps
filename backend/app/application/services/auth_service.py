from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from pydantic import BaseModel

from app.core.config import settings
from app.shared.exceptions import UnauthorizedError, ValidationError


class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[int] = None
    scopes: list[str] = []


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: int
    username: str


class AuthService:
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.SECRET_KEY = settings.SECRET_KEY
        self.ALGORITHM = "HS256"
        self.ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Generate password hash"""
        return self.pwd_context.hash(password)

    def create_access_token(
        self,
        data: dict,
        expires_delta: Optional[timedelta] = None,
        scopes: list[str] = None,
    ) -> str:
        """Create JWT access token"""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES
            )

        to_encode.update(
            {"exp": expire, "iat": datetime.utcnow(), "scopes": scopes or []}
        )

        encoded_jwt = jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)
        return encoded_jwt

    def verify_token(self, token: str) -> TokenData:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            username: str = payload.get("sub")
            user_id: int = payload.get("user_id")
            scopes: list = payload.get("scopes", [])

            if username is None or user_id is None:
                raise UnauthorizedError("Invalid token payload")

            return TokenData(username=username, user_id=user_id, scopes=scopes)

        except JWTError:
            raise UnauthorizedError("Invalid token")

    def create_user_token(
        self, user_id: int, username: str, scopes: list[str] = None
    ) -> Token:
        """Create complete user token response"""
        token_data = {"sub": username, "user_id": user_id}

        expires_delta = timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self.create_access_token(
            data=token_data, expires_delta=expires_delta, scopes=scopes or []
        )

        return Token(
            access_token=access_token,
            expires_in=self.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
            user_id=user_id,
            username=username,
        )

    def validate_password_strength(self, password: str) -> bool:
        """Validate password strength - relaxed policy"""
        if len(password) < 6:
            raise ValidationError(
                "password", "Password must be at least 6 characters long"
            )

        return True

    def extract_token_from_header(self, authorization: str) -> str:
        """Extract token from Authorization header"""
        if not authorization:
            raise UnauthorizedError("Authorization header missing")

        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                raise UnauthorizedError("Invalid authentication scheme")
            return token
        except ValueError:
            raise UnauthorizedError("Invalid authorization header format")


# Global auth service instance
auth_service = AuthService()


def get_auth_service() -> AuthService:
    """Dependency to get auth service"""
    return auth_service
