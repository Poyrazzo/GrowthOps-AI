import base64
from cryptography.fernet import Fernet
from django.conf import settings

def _get_fernet() -> Fernet:
    # Django SECRET_KEY might not be 32 bytes URL-safe base64, so we hash it to fit Fernet requirements
    import hashlib
    key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key)
    return Fernet(fernet_key)

def encrypt(text: str) -> str:
    if not text:
        return text
    f = _get_fernet()
    return f.encrypt(text.encode()).decode()

def decrypt(token: str) -> str:
    if not token:
        return token
    f = _get_fernet()
    try:
        return f.decrypt(token.encode()).decode()
    except Exception:
        # If it's already plaintext or an invalid token, just return it for backward compatibility
        return token
