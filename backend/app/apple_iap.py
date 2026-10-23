"""App Store Server API helpers and App Store Server Notification JWS verify."""

from __future__ import annotations

import base64
import logging
import time
from typing import Any

import httpx
import jwt
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding

from app.config import Settings

logger = logging.getLogger("studio.iap")

PROD_BASE = "https://api.storekit.itunes.apple.com"
SANDBOX_BASE = "https://api.storekit-sandbox.itunes.apple.com"

# Apple Root CA - G3 (public). Used to anchor App Store Server Notification x5c chains.
# Source: https://www.apple.com/certificateauthority/
APPLE_ROOT_CA_G3_PEM = b"""-----BEGIN CERTIFICATE-----
MIICQzCCAcmgAwIBAgIILcX8iNLFS5UwCgYIKoZIzj0EAwMwZzEbMBkGA1UEAwwS
QXBwbGUgUm9vdCBDQSAtIEczMSYwJAYDVQQLDB1BcHBsZSBDZXJ0aWZpY2F0aW9u
IEF1dGhvcml0eTETMBEGA1UECgwKQXBwbGUgSW5jLjELMAkGA1UEBhMCVVMwHhcN
MTQwNDMwMTgxOTA2WhcNMzkwNDMwMTgxOTA2WjBnMRswGQYDVQQDDBJBcHBsZSBS
b290IENBIC0gRzMxJjAkBgNVBAsMHUFwcGxlIENlcnRpZmljYXRpb24gQXV0aG9y
aXR5MRMwEQYDVQQKDApBcHBsZSBJbmMuMQswCQYDVQQGEwJVUzB2MBAGByqGSM49
AgEGBSuBBAAiA2IABJjpLz1AcqTtkyJygRMc3RCV8cWjTnHcFBbZDuWmBSp3ZHtf
TjjTuxxEtX/1H7YyYl3J6YRbTzBPEVoA/VhYDKX1DyxNB0cTddqXl5dvMVztK517
IDvYuVTZXpmkOlEKMaNCMEAwHQYDVR0OBBYEFLuw3qFYM4iapIqZ3r6966/ayySr
MA8GA1UdEwEB/wQFMAMBAf8wDgYDVR0PAQH/BAQDAgEGMAoGCCqGSM49BAMDA2gA
MGUCMQCD6cHEFl4aXTQY2e3v9GwOAEZLuN+yRhHFD/3meoyhpmvOwgPUnPWTxnS4
at+qIxUCMG1mihDK1A3UT82NQz60imOlM27jbdoXt2QfyFMm+YhidDkLF1vLUagM
6BgD56KyKA==
-----END CERTIFICATE-----
"""

_APPLE_ROOT_CA_G3 = x509.load_pem_x509_certificate(APPLE_ROOT_CA_G3_PEM)


class AppleIapError(Exception):
    pass


def _apple_api_jwt(settings: Settings) -> str:
    key_id = (settings.apple_iap_key_id or "").strip()
    issuer = (settings.apple_iap_issuer_id or "").strip()
    private_key = (settings.apple_iap_private_key or "").strip().replace("\\n", "\n")
    bundle = (settings.apple_iap_bundle_id or "com.example.studio.app").strip()
    if not key_id or not issuer or not private_key:
        raise AppleIapError("Apple IAP API credentials are not configured")
    now = int(time.time())
    payload = {
        "iss": issuer,
        "iat": now,
        "exp": now + 20 * 60,
        "aud": "appstoreconnect-v1",
        "bid": bundle,
    }
    return jwt.encode(
        payload,
        private_key,
        algorithm="ES256",
        headers={"kid": key_id, "alg": "ES256", "typ": "JWT"},
    )


async def fetch_transaction_info(settings: Settings, transaction_id: str) -> dict[str, Any]:
    """Load transaction from Apple (tries Production then Sandbox)."""
    token = _apple_api_jwt(settings)
    headers = {"Authorization": f"Bearer {token}"}
    tid = transaction_id.strip()
    async with httpx.AsyncClient(timeout=20.0) as client:
        last_error: str | None = None
        for base in (PROD_BASE, SANDBOX_BASE):
            url = f"{base}/inApps/v1/transactions/{tid}"
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                signed = data.get("signedTransactionInfo")
                if isinstance(signed, str) and signed:
                    # Server API channel is TLS-trusted; still verify x5c when present.
                    return decode_and_verify_jws(signed, require_signature=True)
                return data
            last_error = f"{base} → {resp.status_code}: {resp.text[:200]}"
            if resp.status_code not in {404, 400}:
                if resp.status_code in {401, 403}:
                    raise AppleIapError(last_error)
        raise AppleIapError(last_error or "Transaction not found")


def _b64url_decode(segment: str) -> bytes:
    pad = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + pad)


def _load_x5c_certs(x5c: list[str]) -> list[x509.Certificate]:
    certs: list[x509.Certificate] = []
    for entry in x5c:
        raw = base64.b64decode(entry)
        certs.append(x509.load_der_x509_certificate(raw))
    return certs


def _cert_is_apple_root(cert: x509.Certificate) -> bool:
    return cert.public_bytes(Encoding.DER) == _APPLE_ROOT_CA_G3.public_bytes(Encoding.DER)


def _verify_signed_by(issuer: x509.Certificate, subject: x509.Certificate) -> None:
    pub = issuer.public_key()
    try:
        if isinstance(pub, ec.EllipticCurvePublicKey):
            pub.verify(
                subject.signature,
                subject.tbs_certificate_bytes,
                ec.ECDSA(subject.signature_hash_algorithm),  # type: ignore[arg-type]
            )
            return
        from cryptography.hazmat.primitives.asymmetric import padding, rsa

        if isinstance(pub, rsa.RSAPublicKey):
            pub.verify(
                subject.signature,
                subject.tbs_certificate_bytes,
                padding.PKCS1v15(),
                subject.signature_hash_algorithm,  # type: ignore[arg-type]
            )
            return
    except Exception as exc:
        raise AppleIapError(f"Invalid App Store certificate chain: {exc}") from exc
    raise AppleIapError("Unsupported certificate public key type")


def _verify_cert_chain(certs: list[x509.Certificate]) -> x509.Certificate:
    """Validate leaf→…→Apple Root CA-G3 chain. Returns leaf cert."""
    if not certs:
        raise AppleIapError("JWS missing x5c certificate chain")
    leaf = certs[0]
    # Drop a trailing copy of the Apple root if Apple included it in x5c.
    chain = [c for c in certs if not _cert_is_apple_root(c)]
    if not chain:
        raise AppleIapError("JWS certificate chain empty after root filter")
    # Each cert signed by the next; the last is signed by Apple Root CA - G3.
    for i, cert in enumerate(chain):
        issuer = chain[i + 1] if i + 1 < len(chain) else _APPLE_ROOT_CA_G3
        _verify_signed_by(issuer, cert)
    return leaf


def decode_and_verify_jws(jws: str, *, require_signature: bool = True) -> dict[str, Any]:
    """Decode StoreKit / ASSN JWS. When require_signature=True, verify x5c + ES256."""
    token = (jws or "").strip()
    if token.count(".") != 2:
        raise AppleIapError("Invalid JWS format")

    try:
        header = jwt.get_unverified_header(token)
    except Exception as exc:
        raise AppleIapError(f"Invalid JWS header: {exc}") from exc

    alg = str(header.get("alg") or "")
    if require_signature and alg not in {"ES256", "ES384"}:
        raise AppleIapError(f"Unsupported JWS alg: {alg or 'missing'}")

    x5c = header.get("x5c")
    if require_signature:
        if not isinstance(x5c, list) or not x5c:
            raise AppleIapError("JWS missing x5c (cannot verify signature)")
        try:
            certs = _load_x5c_certs([str(c) for c in x5c])
            leaf = _verify_cert_chain(certs)
            public_key = leaf.public_key()
            algorithms = [alg] if alg else ["ES256"]
            return jwt.decode(
                token,
                key=public_key,  # type: ignore[arg-type]
                algorithms=algorithms,
                options={"verify_aud": False},
            )
        except AppleIapError:
            raise
        except jwt.PyJWTError as exc:
            raise AppleIapError(f"JWS signature verification failed: {exc}") from exc
        except Exception as exc:
            raise AppleIapError(f"JWS verification failed: {exc}") from exc

    # Trusted channel only (legacy path): decode payload without signature.
    try:
        return jwt.decode(token, options={"verify_signature": False})
    except Exception as exc:
        raise AppleIapError(f"Invalid transaction JWS: {exc}") from exc


def decode_transaction_jws(jws: str) -> dict[str, Any]:
    """Decode + verify App Store JWS (ASSN and signedTransactionInfo).

    Requires a valid x5c chain rooted at Apple Root CA - G3.
    """
    return decode_and_verify_jws(jws, require_signature=True)


def period_end_from_tx_info(tx_info: dict[str, Any]):
    """Parse Apple expiresDate (ms since epoch) to aware UTC datetime, or None."""
    from datetime import datetime, timezone

    expires_ms = tx_info.get("expiresDate") or tx_info.get("expires_date")
    if expires_ms is None:
        return None
    try:
        return datetime.fromtimestamp(int(expires_ms) / 1000.0, tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def tx_is_revoked(tx_info: dict[str, Any]) -> bool:
    rev = tx_info.get("revocationDate") or tx_info.get("revocation_date")
    return rev is not None and str(rev).strip() not in {"", "0", "None"}
