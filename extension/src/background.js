/* global EXTENSION_CONFIG, DEFAULT_EXTENSION_SETTINGS, getExtensionSettings, saveExtensionSettings */
importScripts('src/config.js');

const JOB_SAVE_EVENT = 'SAVE_JOB_DETAILS';
const JOB_DETAILS_TELEMETRY = 'JOB_DETAILS_DETECTED';

async function ensureDefaultsInitialized() {
    if (!chrome.storage || !chrome.storage.sync) {
        return;
    }

    return new Promise((resolve) => {
        chrome.storage.sync.get(DEFAULT_EXTENSION_SETTINGS, (stored) => {
            if (chrome.runtime.lastError) {
                console.warn('Job Collector: unable to read defaults', chrome.runtime.lastError);
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
                    console.warn('Job Collector: unable to initialize defaults', chrome.runtime.lastError);
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

    if (settings.apiKey) {
        headers['Authorization'] = `Bearer ${settings.apiKey}`;
    }

    const body = {
        job: payload.job,
        notes: payload.notes || '',
        source: settings.sourceLabel || DEFAULT_EXTENSION_SETTINGS.sourceLabel,
        capturedAt: new Date().toISOString()
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
                console.error('Job Collector: failed to submit job', error);
                sendResponse({ success: false, error: error.message });
            });
        return true; // keep the channel open for async sendResponse
    }

    if (message.type === JOB_DETAILS_TELEMETRY) {
        // Passive telemetry for debugging; nothing persisted for now
        console.debug('Job Collector: telemetry', message.payload?.job?.title);
        sendResponse({ acknowledged: true });
        return false;
    }

    return false;
});
