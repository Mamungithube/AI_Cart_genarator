import os
import hmac
from django.conf import settings
from rest_framework.permissions import BasePermission


class HasAPIKey(BasePermission):
    """
    Validates API authentication using API_SECRET_KEY.
    Accepts key via:
      - Header: 'X-API-KEY: <key>' (or 'HTTP_X_API_KEY')
      - Header: 'Authorization: Bearer <key>' or 'Authorization: ApiKey <key>'
      - Query parameter: '?api_key=<key>' or '?key=<key>'
    """
    message = "Authentication failed: Valid API key required in 'X-API-KEY' header or 'Authorization' header."

    def has_permission(self, request, view):
        expected_key = getattr(settings, 'API_SECRET_KEY', None) or os.getenv('API_SECRET_KEY', '')

        # 1. Header: X-API-KEY / x-api-key
        provided_key = (
            request.META.get('HTTP_X_API_KEY') or
            request.headers.get('x-api-key') or
            request.headers.get('X-API-Key')
        )

        # 2. Header: Authorization (Bearer <key> or Api-Key <key> or ApiKey <key>)
        if not provided_key:
            auth_header = request.headers.get('Authorization') or request.META.get('HTTP_AUTHORIZATION') or ''
            if auth_header:
                parts = auth_header.strip().split()
                if len(parts) == 2 and parts[0].lower() in ('bearer', 'apikey', 'api-key', 'token'):
                    provided_key = parts[1]
                elif len(parts) == 1:
                    provided_key = parts[0]

        # 3. Query Parameter: api_key or key
        if not provided_key and hasattr(request, 'query_params'):
            provided_key = request.query_params.get('api_key') or request.query_params.get('key')
        if not provided_key and hasattr(request, 'GET'):
            provided_key = request.GET.get('api_key') or request.GET.get('key')

        if expected_key:
            if not provided_key:
                return False
            # Constant-time comparison to prevent timing attacks
            return hmac.compare_digest(str(provided_key).strip(), str(expected_key).strip())

        # If no expected key is configured in settings/env, require header to be present
        return provided_key is not None
