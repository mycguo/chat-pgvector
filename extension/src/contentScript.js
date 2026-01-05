const JOB_REQUEST_EVENT = 'REQUEST_PAGE_CONTENT';

function capturePageContent() {
    const title = document.title || null;
    const url = window.location.href;
    const selection = window.getSelection()?.toString().trim();
    const bodyText = document.body ? document.body.innerText : '';
    const primaryText = selection || bodyText;

    // Detect logged-in user handle and Member ID from LinkedIn
    let linkedinHandle = null;
    let linkedinMemberId = null;
    try {
        // 1. Try to get handle from "Me" link
        const profileLink = document.querySelector('a.global-nav__primary-link[href*="/in/"]');
        if (profileLink) {
            const href = profileLink.getAttribute('href');
            const match = href.match(/\/in\/([^\/?#]+)/);
            if (match) {
                linkedinHandle = match[1];
            }
        }

        // 2. Try to get Member ID from script tags (often found in dust or ember data)
        const scripts = document.querySelectorAll('script');
        for (const script of scripts) {
            const content = script.textContent;
            if (content.includes('memberId')) {
                const match = content.match(/"memberId"\s*:\s*"(\d+)"/);
                if (match) {
                    linkedinMemberId = match[1];
                    break;
                }
            }
        }

        // 3. Fallback: try to find any mention of "member:" which is often used in tracking
        if (!linkedinMemberId) {
            const match = document.body.innerHTML.match(/member:(\d+)/);
            if (match) {
                linkedinMemberId = match[1];
            }
        }
    } catch (e) {
        console.warn('Job Tracker: could not detect LinkedIn identity', e);
    }

    return {
        title,
        url,
        text: primaryText?.trim() || null,
        fullText: bodyText?.trim() || null,
        linkedinHandle,
        linkedinMemberId,
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
