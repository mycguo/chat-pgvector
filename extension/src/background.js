const DEFAULT_EXTENSION_SETTINGS = {
    apiEndpoint: "https://jobmaster.streamlit.app/api/jobs",
    apiUserId: ""
};

const EXTENSION_CONFIG = Object.freeze({
    defaultIntakeUrl: DEFAULT_EXTENSION_SETTINGS.apiEndpoint,
    storageKey: "jobCollectorSettings",
    metadataVersion: 1
});

function hasSyncStorage() {
    return Boolean(globalThis.chrome && chrome.storage && chrome.storage.sync);
}

function getExtensionSettings() {
    return new Promise((resolve) => {
        if (!hasSyncStorage()) {
            resolve({ ...DEFAULT_EXTENSION_SETTINGS });
            return;
        }

        chrome.storage.sync.get(DEFAULT_EXTENSION_SETTINGS, (stored) => {
            if (chrome.runtime && chrome.runtime.lastError) {
                console.warn('Job Tracker: storage read failed', chrome.runtime.lastError);
                resolve({ ...DEFAULT_EXTENSION_SETTINGS });
                return;
            }

            resolve({ ...DEFAULT_EXTENSION_SETTINGS, ...stored });
        });
    });
}

function saveExtensionSettings(updates) {
    return new Promise((resolve, reject) => {
        if (!hasSyncStorage()) {
            reject(new Error('Chrome storage is unavailable'));
            return;
        }

        chrome.storage.sync.set(updates, () => {
            if (chrome.runtime && chrome.runtime.lastError) {
                reject(chrome.runtime.lastError);
                return;
            }

            resolve({ ...updates });
        });
    });
}

const JOB_SAVE_EVENT = 'SAVE_JOB_DETAILS';

async function ensureDefaultsInitialized() {
    if (!chrome.storage || !chrome.storage.sync) {
        return;
    }

    return new Promise((resolve) => {
        chrome.storage.sync.get(DEFAULT_EXTENSION_SETTINGS, (stored) => {
            if (chrome.runtime.lastError) {
                console.warn('Job Tracker: unable to read defaults', chrome.runtime.lastError);
                resolve();
                return;
            }

            const updates = {};
            for (const [key, value] of Object.entries(DEFAULT_EXTENSION_SETTINGS)) {
                if (!stored[key]) {
                    updates[key] = value;
                }
            }

            if (Object.keys(updates).length === 0) {
                resolve();
                return;
            }

            chrome.storage.sync.set(updates, () => {
                if (chrome.runtime.lastError) {
                    console.warn('Job Tracker: unable to initialize defaults', chrome.runtime.lastError);
                }
                resolve();
            });
        });
    });
}

async function submitJobDetails(payload) {
    const settings = await getExtensionSettings();
    const endpoint = settings.apiEndpoint || EXTENSION_CONFIG.defaultIntakeUrl;

    const headers = {
        'Content-Type': 'application/json'
    };

    const body = {
        job_url: payload.jobUrl,
        page_title: payload.pageTitle,
        page_content: payload.pageContent,
        user_id: payload.userId || settings.apiUserId || undefined,
        linkedin_handle: payload.linkedinHandle || undefined,
        linkedin_member_id: payload.linkedinMemberId || undefined,
        status: 'tracking',
        notes: payload.notes || '',
        captured_at: new Date().toISOString()
    };

    const response = await fetch(endpoint, {
        method: 'POST',
        headers,
        body: JSON.stringify(body)
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || `API responded with ${response.status}`);
    }

    const data = await response.json().catch(() => ({}));
    return data;
}

chrome.runtime.onInstalled.addListener(() => {
    ensureDefaultsInitialized();
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (!message || !message.type) {
        return false;
    }

    if (message.type === JOB_SAVE_EVENT) {
        submitJobDetails(message.payload)
            .then((result) => {
                sendResponse({ success: true, result });
            })
            .catch((error) => {
                console.error('Job Tracker: failed to submit job', error);
                sendResponse({ success: false, error: error.message });
            });
        return true; // keep the channel open for async sendResponse
    }

    return false;
});
