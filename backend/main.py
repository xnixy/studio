"""ASGI entry for FastAPI Cloud / `fastapi run` auto-discovery.

Cloud runs production mode without a path argument. Prefer importing the
package app so site-packages installs still resolve.
"""

from app.main import app

__all__ = ["app"]
