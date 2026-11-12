"""Every API route needs credentials, except the documented public ones.

See docs/security-review.md.
"""

import re
import uuid

from fastapi.testclient import TestClient

# Public by design: liveness and readiness probes, Prometheus metrics (kept off the web proxy),
# the three auth entry points, and the OpenAPI documentation.
PUBLIC = {
    ("GET", "/health/live"),
    ("GET", "/health/ready"),
    ("GET", "/metrics"),
    ("POST", "/auth/register"),
    ("POST", "/auth/login"),
    ("POST", "/auth/refresh"),
}


def test_every_non_public_route_refuses_requests_without_credentials(client: TestClient) -> None:
    schema = client.app.openapi()  # type: ignore[attr-defined]
    checked = 0
    for path, operations in schema["paths"].items():
        for method in operations:
            if (method.upper(), path) in PUBLIC:
                continue
            concrete = re.sub(
                r"\{[^}]+\}", lambda m: "1" if m[0] == "{number}" else str(uuid.uuid4()), path
            )
            response = client.request(method.upper(), concrete)
            assert response.status_code == 401, (
                f"{method.upper()} {path} gave {response.status_code}"
            )
            checked += 1
    assert checked >= 18  # all routes listed in docs/security-review.md


def test_the_public_list_matches_the_routes_that_exist(client: TestClient) -> None:
    schema = client.app.openapi()  # type: ignore[attr-defined]
    existing = {(m.upper(), p) for p, ops in schema["paths"].items() for m in ops}
    assert existing >= PUBLIC
