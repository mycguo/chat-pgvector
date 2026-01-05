"""Custom Tornado handler for /api/jobs endpoint."""

from __future__ import annotations

import gc
import json
import logging
import os
from typing import Any, Dict, Optional

import tornado.web
from streamlit import config
from streamlit.web.server.server_util import make_url_path_regex

from models.application import create_application
from storage.json_db import JobSearchDB
from storage.user_utils import sanitize_user_id
from ai.job_parser import extract_job_details

LOGGER = logging.getLogger(__name__)

_ROUTE_REGISTERED = False
_RETRY_SCHEDULED = False


def _find_tornado_app() -> Optional[tornado.web.Application]:
    """Locate the active Tornado application instance used by Streamlit."""

    for obj in gc.get_objects():
        try:
            if isinstance(obj, tornado.web.Application):
                return obj
        except ReferenceError:
            continue
    return None


class JobsApiHandler(tornado.web.RequestHandler):
    """Handle POST requests from the Chrome extension."""

    def check_xsrf_cookie(self) -> None:  # type: ignore[override]
        """Disable XSRF protection for API requests."""
        return

    def set_default_headers(self) -> None:
        # CORS: allow extension origins and simple curl testing
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.set_header(
            "Access-Control-Allow-Headers",
            "Content-Type, Authorization, X-Requested-With",
        )
        self.set_header("Content-Type", "application/json")
        self.set_header("Cache-Control", "no-store")

    def options(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        self.set_status(204)
        self.finish()

    def post(self, *args: Any, **kwargs: Any) -> None:  # type: ignore[override]
        LOGGER.info(
            "Incoming /api/jobs request: ip=%s, headers=%s",
            self.request.remote_ip,
            dict(self.request.headers),
        )
        payload = self._parse_body()
        if payload is None:
            return

        notes_value = payload.get("notes")
        if isinstance(notes_value, str):
            notes_value = notes_value.strip() or None

        job_url = payload.get("job_url") or payload.get("jobUrl")

        page_content = payload.get("page_content") or payload.get("pageContent")
        if not page_content:
            self._write_error(400, "page_content is required.")
            return

        try:
            user_id = _resolve_user_id(payload)
            if not user_id:
                self._write_error(
                    401,
                    "Unauthorized: User email not configured in extension settings. "
                    "Please set your Email in the extension options."
                )
                return

            db = JobSearchDB(user_id=user_id)
            parsed = extract_job_details(page_content, job_url=job_url)
            if not parsed.get("company") or not parsed.get("role"):
                LOGGER.warning(
                    "Extraction failed for job: url=%s. Parsed fields: %s",
                    job_url,
                    parsed,
                )
                self._write_error(
                    422, "Failed to extract company or role from job content."
                )
                return
            status_value = (payload.get("status") or "tracking").lower()
            application = create_application(
                company=parsed["company"],
                role=parsed["role"],
                job_url=job_url or parsed.get("apply_url"),
                job_description=parsed.get("description"),
                location=parsed.get("location"),
                salary_range=parsed.get("salary_range"),
                notes=notes_value,
                status=status_value,
            )
            db.add_application(application)
        except ValueError as exc:
            self._write_error(409, str(exc))
            return
        except Exception as exc:
            LOGGER.exception("Failed to persist job via /api/jobs")
            self._write_error(500, "Unable to save application. Check server logs.")
            return

        self.finish(
            {
                "success": True,
                "application_id": application.id,
                "company": application.company,
                "role": application.role,
                "parsed_job": parsed,
            }
        )
        LOGGER.info(
            "Saved job via API: user=%s company=%s role=%s status=%s",
            user_id,
            application.company,
            application.role,
            application.status,
        )

    def _parse_body(self) -> Optional[Dict[str, Any]]:
        if not self.request.body:
            self._write_error(400, "Request body is required.")
            return None

        try:
            return json.loads(self.request.body.decode("utf-8"))
        except json.JSONDecodeError:
            self._write_error(400, "Invalid JSON payload.")
            return None

    def _write_error(self, status_code: int, message: str) -> None:
        self.set_status(status_code)
        self.finish({"success": False, "error": message})


def _resolve_user_id(payload: Dict[str, Any]) -> Optional[str]:
    """
    Determine which JobSearch user bucket should store this job.
    Ensures user_id is prefixed with 'linkedin_'.
    """

    # 1. Allow explicit override in payload
    user_id = payload.get("user_id")

    # 2. Global default from environment if not in payload
    if not user_id:
        user_id = os.getenv("JOB_SEARCH_API_USER_ID")

    if not user_id:
        return None

    # Always ensure linkedin_ prefix and sanitize
    user_id = str(user_id).strip().lower()
    if not user_id.startswith("linkedin_"):
        user_id = f"linkedin_{user_id}"

    return sanitize_user_id(user_id)


def register_jobs_api_route(force: bool = False) -> None:
    """Register the /api/jobs route with the running Tornado app."""

    global _ROUTE_REGISTERED
    if _ROUTE_REGISTERED and not force:
        return

    app = _find_tornado_app()
    if app is None:
        _schedule_retry()
        return

    base = config.get_option("server.baseUrlPath")
    pattern = make_url_path_regex(base, "api", "jobs")

    try:
        # Tornado's add_handlers prepends rules to the router, so the latest 
        # registration will take precedence over older ones.
        app.add_handlers(r".*$", [(pattern, JobsApiHandler)])
        _ROUTE_REGISTERED = True
        LOGGER.info("Registered /api/jobs endpoint (prepended for precedence)")
    except Exception as e:
        LOGGER.error("Failed to add Tornado handler: %s", e)
        _ROUTE_REGISTERED = False


def _schedule_retry(delay_seconds: float = 1.0) -> None:
    global _RETRY_SCHEDULED
    if _RETRY_SCHEDULED:
        return

    try:
        import threading

        def _retry() -> None:
            global _RETRY_SCHEDULED
            _RETRY_SCHEDULED = False
            register_jobs_api_route()

        timer = threading.Timer(delay_seconds, _retry)
        timer.daemon = True
        timer.start()
        _RETRY_SCHEDULED = True
        LOGGER.debug("Scheduled retry to register /api/jobs handler")
    except Exception:
        LOGGER.warning("Unable to schedule retry for /api/jobs handler")
