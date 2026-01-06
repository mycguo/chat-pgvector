const form = document.getElementById('settings-form');
const endpointInput = document.getElementById('api-endpoint');
const statusEl = document.getElementById('settings-status');

const DEFAULTS = {
    apiEndpoint: 'https://jobmaster.streamlit.app/api/jobs'
};

function getSettings() {
    return new Promise((resolve) => {
        chrome.storage.sync.get(DEFAULTS, (stored) => {
            if (chrome.runtime.lastError) {
                console.warn('Job Tracker: storage read failed', chrome.runtime.lastError);
                resolve({ ...DEFAULTS });
                return;
            }
            resolve({ ...DEFAULTS, ...stored });
        });
    });
}

function saveSettings(updates) {
    return new Promise((resolve, reject) => {
        chrome.storage.sync.set(updates, () => {
            if (chrome.runtime.lastError) {
                reject(chrome.runtime.lastError);
                return;
            }
            resolve();
        });
    });
}

async function loadSettings() {
    const settings = await getSettings();
    endpointInput.value = settings.apiEndpoint;
}

function showStatus(message, type = 'info') {
    statusEl.textContent = message;
    statusEl.dataset.variant = type;
}

form.addEventListener('submit', async (event) => {
    event.preventDefault();
    showStatus('Saving settings...');

    try {
        await saveSettings({
            apiEndpoint: endpointInput.value.trim() || DEFAULTS.apiEndpoint
        });
        showStatus('Settings saved successfully.', 'success');
    } catch (error) {
        console.error('Job Tracker: unable to save settings', error);
        showStatus('Failed to save settings. Check console for details.', 'error');
    }
});

document.addEventListener('DOMContentLoaded', loadSettings);
