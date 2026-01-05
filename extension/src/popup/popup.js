const REQUEST_EVENT = 'REQUEST_PAGE_CONTENT';
const SAVE_EVENT = 'SAVE_JOB_DETAILS';

const pageTitleEl = document.getElementById('page-title');
const pageUrlEl = document.getElementById('page-url');
const notesEl = document.getElementById('job-notes');
const saveButton = document.getElementById('save-job');
const statusMessage = document.getElementById('status-message');

let currentPageData = null;

function setStatus(message, type = 'info') {
    statusMessage.textContent = message;
    statusMessage.dataset.variant = type;
}

function renderPageInfo(data) {
    if (!data) {
        pageTitleEl.textContent = 'No job detected';
        pageUrlEl.textContent = '';
        saveButton.disabled = true;
        currentPageData = null;
        return;
    }

    pageTitleEl.textContent = data.title || 'LinkedIn job page';
    pageUrlEl.textContent = data.url || '';
    saveButton.disabled = false;
    currentPageData = data;
}

async function requestPageContent() {
    setStatus('Capturing page content...');

    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) {
        setStatus('No active tab found.');
        return;
    }

    chrome.tabs.sendMessage(tab.id, { type: REQUEST_EVENT }, (response) => {
        if (chrome.runtime.lastError) {
            console.warn('Job Collector: unable to reach content script', chrome.runtime.lastError);
            setStatus('Reload the LinkedIn job page and try again.');
            return;
        }

        if (!response || !response.success) {
            setStatus('Unable to read the page yet. Scroll or reload and retry.', 'warning');
            return;
        }

        renderPageInfo(response.data);
        if (!/linkedin\.com\/jobs/i.test(response.data?.url || '')) {
            setStatus('This extension only works on LinkedIn job pages.', 'warning');
            saveButton.disabled = true;
            return;
        }

        if (!response.data?.fullText) {
            setStatus('Could not capture enough job text. Scroll the page and try again.', 'warning');
            saveButton.disabled = true;
            return;
        }

        setStatus('Ready to add this job.');
    });
}

function handleSaveClick() {
    if (!currentPageData || !currentPageData.fullText) {
        setStatus('Job content not available yet.', 'warning');
        return;
    }

    saveButton.disabled = true;
    setStatus('Sending job to Job Search...');

    const payload = {
        jobUrl: currentPageData.url,
        pageTitle: currentPageData.title,
        pageContent: currentPageData.fullText,
        notes: notesEl.value.trim()
    };

    chrome.runtime.sendMessage({ type: SAVE_EVENT, payload }, (response) => {
        saveButton.disabled = false;
        if (chrome.runtime.lastError) {
            console.error('Job Collector: background error', chrome.runtime.lastError);
            setStatus('Extension background is unavailable. Try again.', 'error');
            return;
        }

        if (!response || !response.success) {
            setStatus(response?.error || 'Job save failed.', 'error');
            return;
        }

        setStatus('Job added successfully! 🎉', 'success');
        notesEl.value = '';
    });
}

saveButton.addEventListener('click', handleSaveClick);
document.addEventListener('DOMContentLoaded', () => {
    requestPageContent();
});
