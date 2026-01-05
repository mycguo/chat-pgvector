# Job Search Collector Chrome Extension

Capture LinkedIn job details from the currently viewed job listing and send them to the Job Search Streamlit application.

## Features

- Captures the current LinkedIn job page text and sends it to the backend API.
- Backend API (GPT-mini) extracts company, role, and other metadata before inserting into the Job Search app.
- Simple popup with a single "Add to my applications" action plus optional notes.
- Configurable API endpoint, API key, and source label via the options page.
- Background service worker handles authenticated POST requests to the Job Search app.

## Structure

```
extension/
├── assets/
│   └── icons/ (16px, 48px, 128px PNGs)
├── manifest.json
├── README.md
└── src/
    ├── background.js       # Service worker (submits jobs to backend)
    ├── config.js           # Shared defaults + storage helpers
    ├── contentScript.js    # Runs on LinkedIn job pages and extracts data
    ├── options/
    │   ├── options.css
    │   ├── options.html
    │   └── options.js
    └── popup/
        ├── popup.css
        ├── popup.html
        └── popup.js
```

## Local Development

1. Open `chrome://extensions` → enable **Developer mode**.
2. Click **Load unpacked** and select the `extension/` folder.
3. (Optional) Open the extension card → **Extension options** to configure the API endpoint and API key. Defaults point to `http://localhost:8501/api/jobs`.
4. Visit `https://www.linkedin.com/jobs/…`, open the extension popup, add optional notes, and click **Add to my applications**.

## Backend Expectations

The background worker posts JSON payloads like:

```json
{
  "job": {
    "title": "Staff Software Engineer",
    "company": "Example",
    "jobId": "123456789",
    "jobUrl": "https://www.linkedin.com/jobs/view/123456789/",
    "location": "New York, NY",
    "description": "…",
    "seniorityLevel": "Senior",
    "employmentType": "Full-time",
    "applyUrl": "https://www.linkedin.com/jobs/view/123456789/apply/"
  },
  "notes": "Spoke with recruiter",
  "source": "linkedin-job-page",
  "capturedAt": "2025-01-04T22:34:12.120Z"
}
```

Ensure the Streamlit app exposes an endpoint (default `POST /api/jobs`) that accepts `{ job_url, page_content, notes }`, runs GPT-mini to extract job details, and persists them. The provided Streamlit server already registers this route; set the `JOB_SEARCH_API_USER_ID` environment variable if you want API submissions to be stored under a specific user profile (defaults to `default_user`).

## Customization Tips

- Update `host_permissions` in `manifest.json` if your Job Search backend runs somewhere other than `http://localhost:8501`.
- Replace the placeholder icons under `assets/icons/` with production artwork before publishing.
- Extend `src/contentScript.js` with additional selectors if LinkedIn changes its DOM structure.
