const REQUEST_EVENT = 'REQUEST_JOB_DETAILS';
const SAVE_EVENT = 'SAVE_JOB_DETAILS';

const titleEl = document.getElementById('job-title');
const companyEl = document.getElementById('job-company');
const locationEl = document.getElementById('job-location');
const workplaceEl = document.getElementById('job-workplace');
const notesEl = document.getElementById('job-notes');
const saveButton = document.getElementById('save-job');
const statusMessage = document.getElementById('status-message');

let currentJob = null;

function setStatus(message, type = 'info') {
    statusMessage.textContent = message;
    statusMessage.dataset.variant = type;
}

function renderJob(job) {
    if (!job) {
        titleEl.textContent = 'No job detected';
        companyEl.textContent = '-';
        locationEl.textContent = '-';
        workplaceEl.textContent = '-';
        saveButton.disabled = true;
        return;
    }

    titleEl.textContent = job.title || 'Unknown title';
    companyEl.textContent = job.company || 'Unknown company';
    locationEl.textContent = job.location || 'Unknown location';
    workplaceEl.textContent = job.workplaceType || 'Not specified';
    saveButton.disabled = false;
    currentJob = job;
}

async function requestJobFromActiveTab() {
    setStatus('Detecting job details...');

    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab) {
        setStatus('No active tab found.');
        return;
    }

    if (!/linkedin\.com\/jobs/i.test(tab.url || '')) {
        setStatus('Visit a LinkedIn job page to capture details.', 'warning');
        return;
    }

    chrome.tabs.sendMessage(tab.id, { type: REQUEST_EVENT }, (response) => {
        if (chrome.runtime.lastError) {
            console.warn('Job Collector: unable to reach content script', chrome.runtime.lastError);
            setStatus('Open a job post and refresh the page.');
            return;
        }

        if (!response || !response.success) {
            setStatus('Unable to extract job details yet. Scroll the page and try again.', 'warning');
            return;
        }

        renderJob(response.job);
        setStatus('Ready to send job details.');
    });
}

function handleSaveClick() {
    if (!currentJob) {
        return;
    }

    saveButton.disabled = true;
    setStatus('Sending job to Job Search...');

    const payload = {
        job: currentJob,
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

        setStatus('Job saved successfully! 🎉', 'success');
        notesEl.value = '';
    });
}

saveButton.addEventListener('click', handleSaveClick);
document.addEventListener('DOMContentLoaded', () => {
    requestJobFromActiveTab();
});
