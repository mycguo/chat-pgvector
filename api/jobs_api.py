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
        payload = self._parse_body()
        if payload is None:
            return

        job_data = self._extract_job(payload)
        if job_data is None:
            self._write_error(400, "Both company and role/title are required.")
            return

        notes_value = payload.get("notes")
        if isinstance(notes_value, str):
            notes_value = notes_value.strip() or None

        try:
            db = JobSearchDB(user_id=_resolve_user_id(payload))
            application = create_application(
                company=job_data["company"],
                role=job_data["role"],
                job_url=job_data.get("job_url"),
                job_description=job_data.get("job_description"),
                location=job_data.get("location"),
                salary_range=job_data.get("salary_range"),
                notes=notes_value,
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
            }
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

    def _extract_job(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        job_section = payload.get("job") or {}

        company = (job_section.get("company") or payload.get("company") or "").strip()
        role = (
            job_section.get("role")
            or job_section.get("title")
            or payload.get("role")
            or ""
        ).strip()

        if not company or not role:
            return None

        job_details: Dict[str, Any] = {
            "company": company,
            "role": role,
        }

        optional_fields = {
            "job_url": job_section.get("jobUrl") or job_section.get("jobURL"),
            "job_description": job_section.get("description"),
            "location": job_section.get("location"),
            "salary_range": job_section.get("salaryRange") or job_section.get("salary"),
        }

        for key, value in optional_fields.items():
            if value:
                job_details[key] = value

        return job_details

    def _write_error(self, status_code: int, message: str) -> None:
        self.set_status(status_code)
        self.finish({"success": False, "error": message})


def _resolve_user_id(payload: Dict[str, Any]) -> str:
    """Determine which JobSearch user bucket should store this job."""

    # Allow explicit override in payload, otherwise fall back to env/default
    if payload.get("user_id"):
        return str(payload["user_id"]).strip()

    return os.getenv("JOB_SEARCH_API_USER_ID", "default_user")


def register_jobs_api_route() -> None:
    """Register the /api/jobs route with the running Tornado app."""

    global _ROUTE_REGISTERED
    if _ROUTE_REGISTERED:
        return

    app = _find_tornado_app()
    if app is None:
        _schedule_retry()
        return

    base = config.get_option("server.baseUrlPath")
    pattern = make_url_path_regex(base, "api", "jobs")

    app.add_handlers(r".*$", [(pattern, JobsApiHandler)])
    _ROUTE_REGISTERED = True
    LOGGER.info("Registered /api/jobs endpoint")


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
