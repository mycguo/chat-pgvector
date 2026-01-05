"""LLM-powered job detail extraction for incoming job pages."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from langchain.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

LOGGER = logging.getLogger(__name__)

_PROMPT_TEMPLATE = PromptTemplate(
    input_variables=["job_url", "job_content"],
    template=(
        "You are a structured data extraction assistant.\n"
        "Extract the job application details from the provided job page content.\n"
        "Return ONLY valid JSON with the following keys: company, role, location, description, apply_url, job_id, salary_range.\n"
        "If a field is missing, set it to null.\n"
        "Job URL: {job_url}\n"
        "Job Page Content:\n{job_content}\n"
        "JSON:"
    ),
)


def _get_llm(model_name: str = "gemini-2.5-flash", temperature: float = 0.1) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model=model_name, temperature=temperature)


def extract_job_details(
    job_content: str,
    job_url: Optional[str] = None,
    *,
    model_name: str = "gemini-2.5-flash",
    max_chars: int = 8000,
) -> Dict[str, Any]:
    """Use the chat model to extract job fields from raw content."""

    if not job_content or not job_content.strip():
        raise ValueError("Job content is required for extraction")

    trimmed_content = job_content.strip()
    if len(trimmed_content) > max_chars:
        trimmed_content = trimmed_content[:max_chars]

    prompt = _PROMPT_TEMPLATE.format(
        job_url=job_url or "unknown",
        job_content=trimmed_content,
    )

    llm = _get_llm(model_name=model_name)
    response = llm.invoke(prompt)
    content = getattr(response, "content", None) or response

    if isinstance(content, list):
        content = " ".join(str(part) for part in content)

    if not isinstance(content, str):
        content = str(content)

    try:
        start_idx = content.find("{")
        end_idx = content.rfind("}")
        if start_idx != -1 and end_idx != -1:
            content = content[start_idx : end_idx + 1]
        data = json.loads(content)
    except json.JSONDecodeError:
        LOGGER.warning("Job parser returned non-JSON response: %s", content)
        raise ValueError("LLM returned invalid JSON")

    return {
        "company": _clean_value(data.get("company")),
        "role": _clean_value(data.get("role")),
        "location": _clean_value(data.get("location")),
        "description": _clean_value(data.get("description")),
        "apply_url": _clean_value(data.get("apply_url")),
        "job_id": _clean_value(data.get("job_id")),
        "salary_range": _clean_value(data.get("salary_range")),
    }


def _clean_value(value: Any) -> Optional[str]:
    if value in (None, "", [], {}):
        return None
    return str(value).strip()

