from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.api.v1.metrics import increment_requests


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        endpoint = request.url.path
        increment_requests(response.status_code, endpoint)
        return response
