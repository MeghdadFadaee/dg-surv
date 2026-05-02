from django.conf import settings
from django.http import HttpResponse
from django.utils.cache import patch_vary_headers


class PublicApiCorsMiddleware:
    """Add simple CORS support for the public survey API."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith("/api/") and request.method == "OPTIONS":
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)

        if request.path.startswith("/api/"):
            self._set_cors_headers(request, response)

        return response

    def _set_cors_headers(self, request, response):
        configured_origins = getattr(settings, "SURVEY_API_CORS_ORIGINS", "*")
        origins = [origin.strip() for origin in configured_origins.split(",") if origin.strip()]
        request_origin = request.headers.get("Origin")

        if "*" in origins:
            response["Access-Control-Allow-Origin"] = "*"
        elif request_origin in origins:
            response["Access-Control-Allow-Origin"] = request_origin
            patch_vary_headers(response, ("Origin",))

        response["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        response["Access-Control-Max-Age"] = "86400"
