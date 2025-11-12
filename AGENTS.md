# Repository Guidelines

## Project Structure & Module Organization
- `app.py` bootstraps the Streamlit UI and wires helper modules.
- `ai/` hosts retrieval, matching, and agent logic; keep shared utilities here.
- `pages/` contains Streamlit multipage views; mirror page names to feature names.
- `docs/`, `interview_data/`, `resume_data/`, and `storage/` store seeded content and should remain data-only.
- `tests/` mirrors runtime modules; create parallel test files like `tests/test_feature.py`.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate` creates an isolated environment.
- `pip install -r requirements.txt` installs the Streamlit, LangChain, and vector-store tooling.
- `streamlit run app.py` launches the local UI with live reloading.
- `pytest tests` runs the full automated suite; scope with `-k` for targeted runs.

## Coding Style & Naming Conventions
- Use 4-space indentation, type hints for new public functions, and Python 3.10 features when helpful.
- Keep Streamlit widgets in lower_snake_case blocks and title-case human-facing labels.
- Favor descriptive module names (e.g., `job_matcher.py`) and align page files with their sidebar label.
- Run `black .` or configure your editor to auto-format before opening a PR; import order should match `isort` defaults.

## Testing Guidelines
- Tests rely on `pytest`; name files `test_*.py` and functions `test_should_do_x` to keep discovery simple.
- Mock external APIs (Google Generative AI, Milvus, AssemblyAI) to keep runs offline and deterministic.
- Add regression tests whenever you change retrieval logic, data ingestion, or long-running background jobs.

## Commit & Pull Request Guidelines
- Follow the existing short, imperative style: `verb-scope` summaries under 50 characters (e.g., `update job matcher`).
- Reference relevant issues in the body, explain motivation plus validation steps, and attach screenshots for UI changes.
- Ensure PRs include setup/test instructions and call out any migrations or manual data updates.

## Security & Configuration Tips
- Keep secrets in `.env` (Google, AssemblyAI, Milvus) and never commit credentials or derived cache files.
- Use the provided `milvus_local.db` and `storage/` artifacts for local experiments only; purge sensitive exports before pushing.
