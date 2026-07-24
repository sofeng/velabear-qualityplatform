import hashlib
import hmac

from django.conf import settings


def build_internal_service_signature(scope, resource_id):
    message = f'{scope}:{resource_id}'.encode('utf-8')
    secret = str(settings.SECRET_KEY).encode('utf-8')
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def verify_internal_service_signature(signature, scope, resource_id):
    expected = build_internal_service_signature(scope, resource_id)
    return hmac.compare_digest(str(signature or ''), expected)
