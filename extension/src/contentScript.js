const JOB_REQUEST_EVENT = 'REQUEST_PAGE_CONTENT';

function capturePageContent() {
    const title = document.title || null;
    const url = window.location.href;
    const selection = window.getSelection()?.toString().trim();
    const bodyText = document.body ? document.body.innerText : '';
    const primaryText = selection || bodyText;

    return {
        title,
        url,
        text: primaryText?.trim() || null,
        fullText: bodyText?.trim() || null,
    };
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (!message || message.type !== JOB_REQUEST_EVENT) {
        return false;
    }

    const payload = capturePageContent();
    sendResponse({ success: Boolean(payload.fullText), data: payload });
    return true;
});
