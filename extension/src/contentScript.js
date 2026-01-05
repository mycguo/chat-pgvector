/* global EXTENSION_CONFIG */
const JOB_REQUEST_EVENT = 'REQUEST_JOB_DETAILS';
const JOB_DETAILS_TELEMETRY = 'JOB_DETAILS_DETECTED';

const SELECTORS = {
    title: 'h1.top-card-layout__title',
    company: 'a.topcard__org-name-link, span.topcard__flavor',
    location: 'span.topcard__flavor--bullet',
    workplaceType: 'span[data-job-details="workplace_type"]',
    description: 'div.show-more-less-html__markup'
};

let latestJobDetails = null;
let observer = null;

function getText(selector) {
    const el = document.querySelector(selector);
    if (!el) {
        return null;
    }
    return el.textContent.trim();
}

function getJobIdFromUrl(urlString) {
    try {
        const url = new URL(urlString || window.location.href);
        const parts = url.pathname.split('/').filter(Boolean);
        const numericPart = parts.find((part) => /^\d+$/.test(part));
        return numericPart || null;
    } catch (_) {
        return null;
    }
}

function getDescription() {
    const element = document.querySelector(SELECTORS.description);
    if (!element) {
        return null;
    }
    return element.innerText.trim();
}

function getSeniorityAndEmploymentDetails() {
    const details = {
        seniorityLevel: null,
        employmentType: null,
        industries: null
    };

    const rows = document.querySelectorAll('li.description__job-criteria-item');
    rows.forEach((row) => {
        const key = row.querySelector('h3');
        const value = row.querySelector('span');
        if (!key || !value) {
            return;
        }
        const label = key.textContent.toLowerCase();
        const text = value.textContent.trim();
        if (label.includes('seniority')) {
            details.seniorityLevel = text;
        } else if (label.includes('employment type')) {
            details.employmentType = text;
        } else if (label.includes('industries')) {
            details.industries = text;
        }
    });

    return details;
}

function getApplyLink() {
    const button = document.querySelector('a[data-tracking-control-name="public_jobs_apply-link"]') ||
        document.querySelector('a[data-tracking-control-name="public_jobs_topcard_btn_apply"]') ||
        document.querySelector('a[data-tracking-control-name="jobs_details_topcard_inapply"]');
    if (!button) {
        return window.location.href;
    }
    return button.href;
}

function collectJobDetails() {
    const job = {
        title: getText(SELECTORS.title),
        company: getText(SELECTORS.company),
        location: getText(SELECTORS.location),
        workplaceType: getText(SELECTORS.workplaceType),
        description: getDescription(),
        jobId: getJobIdFromUrl(),
        jobUrl: window.location.href,
        applyUrl: getApplyLink(),
        capturedAt: new Date().toISOString()
    };

    const metadata = getSeniorityAndEmploymentDetails();
    return { ...job, ...metadata };
}

function updateJobDetails() {
    const newDetails = collectJobDetails();
    if (!newDetails.title || !newDetails.company) {
        return;
    }

    const serialized = JSON.stringify(newDetails);
    const previousSerialized = latestJobDetails ? JSON.stringify(latestJobDetails) : null;
    if (serialized === previousSerialized) {
        return;
    }

    latestJobDetails = newDetails;

    if (chrome && chrome.runtime) {
        chrome.runtime.sendMessage({
            type: JOB_DETAILS_TELEMETRY,
            payload: { job: newDetails }
        }, () => {
            // Ignore runtime errors when popup/background is unavailable
        });
    }
}

function startObserving() {
    if (observer) {
        observer.disconnect();
    }

    observer = new MutationObserver(() => {
        updateJobDetails();
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true,
        characterData: true
    });
}

function init() {
    updateJobDetails();
    startObserving();
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (!message || message.type !== JOB_REQUEST_EVENT) {
        return false;
    }

    if (!latestJobDetails) {
        updateJobDetails();
    }

    sendResponse({
        success: Boolean(latestJobDetails && latestJobDetails.title),
        job: latestJobDetails
    });
    return true;
});

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
