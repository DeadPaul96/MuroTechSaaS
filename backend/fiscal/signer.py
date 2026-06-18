"""Firma XMLDSig enveloped para comprobantes MH."""
import zlib

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from lxml import etree
from signxml import XMLSigner, SignatureConstructionMethod


def decrypt_p12_data(p12_data: bytes, encryption_key: str | None = None) -> bytes:
    raw = zlib.decompress(p12_data)
    if not encryption_key:
        return raw
    try:
        return Fernet(encryption_key).decrypt(raw)
    except InvalidToken as err:
        raise ValueError('No se pudo descifrar el P12: clave inválida') from err


def encrypt_p12_data(raw_p12: bytes, encryption_key: str | None = None) -> bytes:
    payload = raw_p12
    if encryption_key:
        payload = Fernet(encryption_key).encrypt(raw_p12)
    return zlib.compress(payload)


def firmar_xml(xml_content, p12_data: bytes, p12_password: str, encryption_key: str | None = None) -> bytes:
    """Firma digital XML con certificado .p12."""
    p12_raw = decrypt_p12_data(p12_data, encryption_key)
    private_key, certificate, _ = pkcs12.load_key_and_certificates(p12_raw, p12_password.encode())
    xml_text = xml_content.decode('utf-8') if isinstance(xml_content, bytes) else str(xml_content)
    root = etree.fromstring(xml_text.encode('utf-8'))
    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    cert_pem = certificate.public_bytes(serialization.Encoding.PEM)
    signer = XMLSigner(method=SignatureConstructionMethod.enveloped, signature_algorithm='rsa-sha256', digest_algorithm='sha256')
    signed_root = signer.sign(root, key=key_pem, cert=cert_pem)
    return etree.tostring(signed_root, encoding='utf-8', xml_declaration=True)
