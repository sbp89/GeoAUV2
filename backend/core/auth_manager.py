"""
Gestor de Autenticación, Tokens HMAC y Registro de Usuarios — GeoAuV2
- Cuenta principal protegida: Usuario `Momentum` (con respaldo en memoria y Supabase).
- Hashing criptográfico PBKDF2-HMAC-SHA256 con sal aleatoria por usuario.
- Tokens de sesión firmados con HMAC-SHA256 compartidos de forma determinística entre instancias serverless.
"""
import base64
import datetime
import hashlib
import hmac
import json
import os
import re
import secrets
import time
from typing import Any, Dict, List, Optional

from backend.services.supabase_service import SupabaseService


PBKDF2_ITERATIONS = 160_000
PRIMARY_USERNAME = "Momentum"


def _b64u_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64u_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def _signing_secret() -> bytes:
    seed = (
        os.getenv("GEOAU_AUTH_SECRET")
        or os.getenv("CRON_SECRET")
        or os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
        or "GeoAuV2_Momentum_Session_Key_2026_Protected"
    )
    return hashlib.sha256(seed.encode("utf-8")).digest()


def hash_password(password: str, salt_hex: Optional[str] = None) -> str:
    """Genera un hash seguro PBKDF2-HMAC-SHA256 con sal de 16 bytes."""
    salt = salt_hex or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verifica una contraseña en tiempo constante contra un hash PBKDF2-HMAC-SHA256."""
    if not password or not stored_hash:
        return False
    try:
        algo, iters_str, salt, digest_hex = stored_hash.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iters = int(iters_str)
        actual_hex = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iters,
        ).hex()
        return hmac.compare_digest(actual_hex, digest_hex)
    except Exception:
        return False


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# Semilla primaria garantizada incluso sin red ni base de datos
_IN_MEMORY_USERS: Dict[str, Dict[str, Any]] = {
    "momentum": {
        "username": "Momentum",
        "username_lower": "momentum",
        "password_hash": hash_password("Momentum1.", salt_hex="7c1e39d825f04b938c9c7d5e6412ab3f"),
        "full_name": "Administrador Principal",
        "role": "admin",
        "created_by": "Sistema",
        "created_at": "2026-01-01T00:00:00+00:00",
        "is_primary": True,
    }
}


def _public_user_dict(record: Dict[str, Any]) -> Dict[str, Any]:
    uname = str(record.get("username", ""))
    return {
        "username": uname,
        "full_name": record.get("full_name", "") or uname,
        "role": record.get("role", "admin"),
        "created_by": record.get("created_by", "Momentum"),
        "created_at": record.get("created_at") or _now_iso(),
        "is_primary": uname.lower() == "momentum",
    }


def _merged_user_map() -> Dict[str, Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {k: dict(v) for k, v in _IN_MEMORY_USERS.items()}
    for row in SupabaseService.list_db_users():
        uname = str(row.get("username") or "").strip()
        if not uname:
            continue
        ulower = uname.lower()
        # Conservar contraseña primaria Momentum1. garantizada si no existe override distinto válido
        if ulower == "momentum" and not row.get("password_hash"):
            continue
        merged[ulower] = {
            "username": uname,
            "username_lower": ulower,
            "password_hash": row.get("password_hash", ""),
            "full_name": row.get("full_name", ""),
            "role": row.get("role", "admin"),
            "created_by": row.get("created_by", "Momentum"),
            "created_at": row.get("created_at") or _now_iso(),
            "is_primary": ulower == "momentum",
        }
    return merged


def create_session_token(username: str, role: str = "admin", ttl_seconds: int = 86400 * 7) -> str:
    payload = {
        "sub": username,
        "role": role,
        "iat": int(time.time()),
        "exp": int(time.time()) + ttl_seconds,
    }
    payload_b64 = _b64u_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = hmac.new(_signing_secret(), payload_b64.encode("ascii"), hashlib.sha256).digest()
    return f"{payload_b64}.{_b64u_encode(sig)}"


def verify_session_token(token: str) -> Optional[Dict[str, Any]]:
    if not token or "." not in token:
        return None
    try:
        payload_b64, sig_b64 = token.split(".", 1)
        expected_sig = hmac.new(_signing_secret(), payload_b64.encode("ascii"), hashlib.sha256).digest()
        provided_sig = _b64u_decode(sig_b64)
        if not hmac.compare_digest(expected_sig, provided_sig):
            return None
        payload = json.loads(_b64u_decode(payload_b64).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        uname = str(payload.get("sub") or "").strip()
        if not uname:
            return None
        return {"username": uname, "role": payload.get("role", "admin")}
    except Exception:
        return None


def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Valida credenciales contra usuarios en memoria y Supabase."""
    uname_clean = (username or "").strip()
    if not uname_clean or not password:
        return None
    ulower = uname_clean.lower()

    users = _merged_user_map()
    record = users.get(ulower)
    if record and verify_password(password, str(record.get("password_hash", ""))):
        return _public_user_dict(record)

    # Garantizar acceso de la cuenta primaria Momentum / Momentum1. incluso si hubiera un registro incompleto en BD
    if ulower == "momentum" and hmac.compare_digest(password, "Momentum1."):
        primary_rec = _IN_MEMORY_USERS["momentum"]
        SupabaseService.upsert_db_user(primary_rec)
        return _public_user_dict(primary_rec)

    return None


def list_users() -> List[Dict[str, Any]]:
    users = _merged_user_map()
    ordered = sorted(
        users.values(),
        key=lambda u: (0 if str(u.get("username", "")).lower() == "momentum" else 1, str(u.get("created_at", ""))),
    )
    return [_public_user_dict(u) for u in ordered]


def create_user(
    username: str,
    password: str,
    full_name: str = "",
    role: str = "admin",
    created_by: str = "Momentum",
) -> Dict[str, Any]:
    uname = (username or "").strip()
    if not re.match(r"^[A-Za-z0-9_.-]{3,60}$", uname):
        raise ValueError(
            "El nombre de usuario debe tener entre 3 y 60 caracteres (solo letras, números, punto, guion o guion bajo)."
        )
    if not password or len(password) < 4:
        raise ValueError("La clave debe tener al menos 4 caracteres.")

    ulower = uname.lower()
    existing = _merged_user_map()
    if ulower in existing:
        raise ValueError(f"El usuario '{uname}' ya existe en el sistema.")

    clean_role = role if role in ("admin", "geologo", "operador", "lector") else "admin"
    record = {
        "username": uname,
        "username_lower": ulower,
        "password_hash": hash_password(password),
        "full_name": (full_name or uname).strip()[:120],
        "role": clean_role,
        "created_by": (created_by or "Momentum")[:60],
        "created_at": _now_iso(),
        "is_primary": False,
    }
    _IN_MEMORY_USERS[ulower] = record
    SupabaseService.upsert_db_user(record)
    return _public_user_dict(record)


def delete_user(username: str) -> bool:
    uname = (username or "").strip()
    ulower = uname.lower()
    if not ulower:
        raise ValueError("Usuario inválido.")
    if ulower == "momentum":
        raise ValueError("La cuenta principal 'Momentum' está protegida y no puede eliminarse.")

    existing = _merged_user_map()
    if ulower not in existing:
        return False

    _IN_MEMORY_USERS.pop(ulower, None)
    SupabaseService.delete_db_user(ulower)
    return True
