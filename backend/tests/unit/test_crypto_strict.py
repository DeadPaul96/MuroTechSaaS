"""Cifrado estricto en producción."""
import pytest

from app.utils.crypto import encrypt_text


def test_encrypt_strict_requires_key():
    with pytest.raises(ValueError, match='ENCRYPTION_KEY'):
        encrypt_text('secret', None, strict=True)
