"""Plaintext secret helpers for the Siyuan-quality edition.

Source deployments do not encrypt credentials at rest; values are stored and
returned as-is. This replaces the former Fernet-based helpers from ai_development.
"""

from __future__ import annotations


def is_serialized_fernet_secret(value) -> bool:
    return False


def encrypt_password(value):
    return '' if value is None else str(value)


def decrypt_password(value):
    return '' if value is None else str(value)


def decrypt_or_repair_secret(value, *, model_instance=None, field_name=''):
    return '' if value is None else str(value)
