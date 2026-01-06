const REQUEST_EVENT = 'REQUEST_PAGE_CONTENT';
const SAVE_EVENT = 'SAVE_JOB_DETAILS';

const openOptionsBtn = document.getElementById('open-options');
const pageTitleEl = document.getElementById('page-title');
const pageUrlEl = document.getElementById('page-url');
const userIdInput = document.getElementById('api-user-id');
const notesEl = document.getElementById('job-notes');
const saveButton = document.getElementById('save-job');
const statusMessage = document.getElementById('status-message');

let currentPageData = null;
let currentSettings = null;
const STORAGE_DEFAULTS = {
    apiUserId: '',
    apiEndpoint: 'http://localhost:8501/api/jobs'
};

async function getSettings() {
    return new Promise((resolve) => {
        chrome.storage.sync.get(STORAGE_DEFAULTS, (stored) => {
            resolve({ ...STORAGE_DEFAULTS, ...stored });
        });
    });
}

function persistSettings(updates) {
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

function setStatus(message, type = 'info') {
    statusMessage.textContent = message;
    statusMessage.dataset.variant = type;
}

function updateSaveButtonState() {
    const hasUser = Boolean(userIdInput.value.trim());
    const hasPage = Boolean(currentPageData && currentPageData.fullText);
    saveButton.disabled = !(hasUser && hasPage);
    if (!hasUser) {
        setStatus('Account email required to continue.', 'warning');
    } else if (!hasPage) {
        setStatus('Open a LinkedIn job post to capture details.', 'warning');
    } else {
        setStatus('Ready to add this job.');
    }
}

function renderPageInfo(data) {
    if (!data) {
        pageTitleEl.textContent = 'No job detected';
        pageUrlEl.textContent = '';
        currentPageData = null;
        updateSaveButtonState();
        return;
    }

    pageTitleEl.textContent = data.title || 'LinkedIn job page';
    pageUrlEl.textContent = data.url || '';
    currentPageData = data;
    updateSaveButtonState();
}

async function requestPageContent() {
    setStatus('Capturing page content...');

    // Refresh settings before capturing
    currentSettings = await getSettings();
    userIdInput.value = currentSettings.apiUserId || '';
    updateSaveButtonState();

    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) {
        setStatus('No active tab found.');
        return;
    }

    chrome.tabs.sendMessage(tab.id, { type: REQUEST_EVENT }, (response) => {
        if (chrome.runtime.lastError) {
            console.warn('Job Tracker: unable to reach content script', chrome.runtime.lastError);
            setStatus('Reload the LinkedIn job page and try again.');
            return;
        }

        if (!response || !response.success) {
            setStatus('Unable to read the page yet. Scroll or reload and retry.', 'warning');
            return;
        }

        if (!/linkedin\.com\/jobs/i.test(response.data?.url || '')) {
            setStatus('This extension only works on LinkedIn job pages.', 'warning');
            return;
        }

        if (!response.data?.fullText) {
            setStatus('Could not capture enough job text. Scroll the page and try again.', 'warning');
            return;
        }

        renderPageInfo(response.data);
        updateSaveButtonState();
    });
}

function handleSaveClick() {
    if (!currentPageData || !currentPageData.fullText) {
        setStatus('Job content not available yet.', 'warning');
        return;
    }

    const userId = userIdInput.value.trim();
    if (!userId) {
        setStatus('Account email is required.', 'error');
        return;
    }

    // Save User ID to storage if it changed
    if (userId !== currentSettings.apiUserId) {
        chrome.storage.sync.set({ apiUserId: userId });
        currentSettings.apiUserId = userId;
    }

    setStatus('Sending job to Job Search...');
    saveButton.disabled = true;

    const payload = {
        jobUrl: currentPageData.url,
        pageTitle: currentPageData.title,
        pageContent: currentPageData.fullText,
        userId: userId,
        notes: notesEl.value.trim()
    };

    chrome.runtime.sendMessage({ type: SAVE_EVENT, payload }, (response) => {
        saveButton.disabled = false;
        if (chrome.runtime.lastError) {
            console.error('Job Tracker: background error', chrome.runtime.lastError);
            setStatus('Extension background is unavailable. Try again.', 'error');
            return;
        }

        if (!response || !response.success) {
            setStatus(response?.error || 'Job save failed.', 'error');
            return;
        }

        setStatus('Job added successfully! 🎉', 'success');
        notesEl.value = '';
        saveButton.disabled = true;
    });
}

userIdInput.addEventListener('input', () => {
    updateSaveButtonState();
});

userIdInput.addEventListener('blur', async () => {
    const trimmed = userIdInput.value.trim();
    currentSettings.apiUserId = trimmed;
    await persistSettings({ apiUserId: trimmed });
});

openOptionsBtn.addEventListener('click', () => {
    chrome.runtime.openOptionsPage();
});

saveButton.addEventListener('click', handleSaveClick);
document.addEventListener('DOMContentLoaded', () => {
    requestPageContent();
});
