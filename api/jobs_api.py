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


def _resolve_user_id(payload: Dict[str, Any]) -> str:
    """Determine which JobSearch user bucket should store this job."""

    # 1. Allow explicit override in payload
    if payload.get("user_id"):
        return str(payload["user_id"]).strip()

    # 2. Try explicit identity mapping for LinkedIn
    linkedin_member_id = payload.get("linkedin_member_id")
    linkedin_handle = payload.get("linkedin_handle")

    if linkedin_member_id or linkedin_handle:
        try:
            from storage.pg_vector_store import PgVectorStore
            # Search in the system-level mapping collection
            store = PgVectorStore(collection_name="system_metadata", user_id="system")
            
            # Try member_id first (more robust)
            if linkedin_member_id:
                mappings = store.list_records(
                    record_type="identity_mapping",
                    filters={"linkedin_sub": str(linkedin_member_id)}
                )
                if mappings:
                    target = mappings[0].get("target_user_id")
                    LOGGER.info("Resolved user_id to %s via member_id %s", target, linkedin_member_id)
                    return target

            # Then try handle (guessing but better than nothing)
            if linkedin_handle:
                # We can't do exact match on the whole directory name easily without a list
                # but we can look for it in the mapping table if we stored it
                # For now, let's keep the legacy folder scan as a fallback
                pass
        except Exception as e:
            LOGGER.warning("Identity mapping lookup failed: %s", e)

    # 3. Legacy scan fallback for LinkedIn extension
    if linkedin_handle:
        user_data_dir = "user_data"
        if os.path.exists(user_data_dir):
            for dirname in os.listdir(user_data_dir):
                if dirname.startswith("linkedin_") and linkedin_handle in dirname:
                    LOGGER.info("Auto-resolved user_id to %s based on folder scan for %s", dirname, linkedin_handle)
                    return dirname

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
