"""RSA encryption utilities for secure password transport."""

import base64

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

_private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048,
)

_public_key_pem = _private_key.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
).decode()


def get_public_key_pem() -> str:
    return _public_key_pem


def decrypt_password(encrypted_b64: str) -> str:
    encrypted = base64.b64decode(encrypted_b64)
    decrypted = _private_key.decrypt(
        encrypted,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return decrypted.decode("utf-8")


def resolve_password(raw: str) -> str:
    """Attempt RSA decryption; fall back to plaintext for backward compat."""
    if len(raw) >= 100:
        try:
            return decrypt_password(raw)
        except Exception:
            pass
    return raw
