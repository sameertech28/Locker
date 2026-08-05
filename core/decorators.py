"""Security decorators for Locker views."""
import functools
import time
from collections import defaultdict

from django.http import JsonResponse


# Simple in-memory rate limiter (use Redis in production)
_rate_limit_store = defaultdict(list)


def rate_limit(max_requests=30, window_seconds=60):
    """Decorator to rate-limit views by authenticated user or IP."""
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.is_authenticated:
                key = f"user:{request.user.id}"
            else:
                key = f"ip:{request.META.get('REMOTE_ADDR', 'unknown')}"

            now = time.time()
            # Purge old entries outside the window
            _rate_limit_store[key] = [
                t for t in _rate_limit_store[key] if now - t < window_seconds
            ]

            if len(_rate_limit_store[key]) >= max_requests:
                return JsonResponse(
                    {"error": "Rate limit exceeded. Please try again later."},
                    status=429,
                )

            _rate_limit_store[key].append(now)
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
