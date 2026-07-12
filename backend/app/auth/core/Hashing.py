import secrets
from passlib.context import CryptContext

pwd_cxt = CryptContext(schemes=["bcrypt"], deprecated="auto")

class Hash:
    @staticmethod
    def bcrypt(password: str) -> str:
        return pwd_cxt.hash(password)

    @staticmethod
    def verify(hashed_password: str, plain_password: str) -> bool:
        return pwd_cxt.verify(plain_password, hashed_password)

    @staticmethod
    def generate_verification_token() -> str:
        return secrets.token_hex(16)