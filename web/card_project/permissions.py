import os
import secrets
from rest_framework import permissions
from rest_framework.exceptions import AuthenticationFailed


class HasAPIKey(permissions.BasePermission):
    """
    Security Permission: Requires a valid fixed API key.
    
    Accepted in:
      1. Header: X-API-KEY: <key> or X-API-Key: <key>
      2. Header: Authorization: Bearer <key> or Api-Key <key>
      3. Query Param: ?api_key=<key> (useful for image links / GET endpoints)
      
    Returns HTTP 401 if missing or invalid.
    """
    def has_permission(self, request, view):
        expected_key = os.environ.get('API_SECRET_KEY', '').strip()
        
        # If no key configured in environment, allow (development fallback)
        if not expected_key:
            return True

        # 1. Header: X-API-KEY / X-API-Key
        provided_key = (
            request.headers.get('X-API-KEY') or
            request.headers.get('X-API-Key') or
            request.META.get('HTTP_X_API_KEY')
        )

        # 2. Header: Authorization (Bearer / Api-Key / Token)
        if not provided_key:
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith(('Bearer ', 'Api-Key ', 'Token ')):
                parts = auth_header.split(' ', 1)
                if len(parts) == 2:
                    provided_key = parts[1].strip()

        # 3. Query parameter (?api_key=...)
        if not provided_key:
            provided_key = request.query_params.get('api_key')

        if not provided_key:
            raise AuthenticationFailed({
                "success": False,
                "error": "Authentication failed: Missing API Key. Provide via 'X-API-KEY' header or 'Authorization: Bearer <key>'."
            })

        # Use constant-time comparison to prevent timing attacks
        if not secrets.compare_digest(provided_key.strip(), expected_key):
            raise AuthenticationFailed({
                "success": False,
                "error": "Authentication failed: Invalid API Key."
            })

        return True
