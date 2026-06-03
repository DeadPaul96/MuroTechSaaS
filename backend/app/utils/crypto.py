"""Cifrado Fernet para secretos en reposo."""
from cryptography.fernet import Fernet, InvalidToken

ENC_PREFIX = 'enc:'

def encrypt_text(plain: str, encryption_key: str, *, strict: bool = False) -> str:
    if not plain:
        return plain
    if not encryption_key:
        if strict:
            raise ValueError('ENCRYPTION_KEY requerida para cifrar secretos')
        return plain
    token = Fernet(encryption_key).encrypt(plain.encode('utf-8')).decode('utf-8')
    return f'{ENC_PREFIX}{token}'

def decrypt_text(value: str, encryption_key: str) -> str:
    if not value:
        return value
    if not str(value).startswith(ENC_PREFIX):
        return value
    if not encryption_key:
        raise ValueError('ENCRYPTION_KEY requerida')
    token = str(value)[len(ENC_PREFIX):]
    try:
        return Fernet(encryption_key).decrypt(token.encode('utf-8')).decode('utf-8')
    except InvalidToken as err:
        raise ValueError('No se pudo descifrar') from err
