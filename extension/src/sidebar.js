(function () {
    if (window.hasOwnProperty('__jt_sidebar_injected')) return;
    window.__jt_sidebar_injected = true;

    const SAVE_EVENT = 'SAVE_JOB_DETAILS';
    let currentSettings = null;
    let currentPageData = null;

    // --- Helper Functions ---
    function getSettings() {
        return new Promise((resolve) => {
            chrome.storage.sync.get(['apiUserId', 'apiEndpoint'], (stored) => {
                resolve(stored || {});
            });
        });
    }

    function capturePageContent() {
        const title = document.title || null;
        const url = window.location.href;
        const bodyText = document.body ? document.body.innerText : '';

        // Identity detection (same as contentScript.js)
        let linkedinHandle = null;
        let linkedinMemberId = null;
        try {
            const profileLink = document.querySelector('a.global-nav__primary-link[href*="/in/"]');
            if (profileLink) {
                const match = profileLink.getAttribute('href').match(/\/in\/([^\/?#]+)/);
                if (match) linkedinHandle = match[1];
            }
            const scripts = document.querySelectorAll('script');
            for (const script of scripts) {
                const match = script.textContent.match(/"memberId"\s*:\s*"(\d+)"/);
                if (match) {
                    linkedinMemberId = match[1];
                    break;
                }
            }
            if (!linkedinMemberId) {
                const match = document.body.innerHTML.match(/member:(\d+)/);
                if (match) linkedinMemberId = match[1];
            }
        } catch (e) { }

        return {
            title,
            url,
            fullText: bodyText.trim(),
            linkedinHandle,
            linkedinMemberId
        };
    }

    // --- UI Creation ---
    async function injectCard() {
        // Target containers for embedding directly in the job details
        const selectors = [
            '.jobs-description',
            '.jobs-details-top-card',
            '.jobs-unified-top-card',
            '.jobs-details__main-content'
        ];

        let target = null;
        for (const selector of selectors) {
            target = document.querySelector(selector);
            if (target) break;
        }

        if (!target) {
            console.warn('Job Tracker: job details container not found');
            return;
        }

        // Avoid double injection
        if (target.querySelector('#jt-card-host')) return;

        const host = document.createElement('div');
        host.id = 'jt-card-host';
        // Prepend to show up at the top of the description/card
        target.prepend(host);

        const shadow = host.attachShadow({ mode: 'open' });

        // Inject Styles
        const styleLink = document.createElement('link');
        styleLink.rel = 'stylesheet';
        styleLink.href = chrome.runtime.getURL('src/sidebar.css');
        shadow.appendChild(styleLink);

        // Build HTML
        const container = document.createElement('div');
        container.id = 'jt-card-container';
        container.innerHTML = `
            <div class="card-inner">
                <div class="card-left">
                    <div class="brand">
                        <img src="${chrome.runtime.getURL('assets/icons/icon48.png')}" alt="" />
                        <span class="brand-name">Job Tracker</span>
                    </div>
                    <div id="jt-status-message" class="status">Ready to track</div>
                    <div id="jt-identity-info" class="identity" style="display: none;">
                        <span id="jt-identity-value"></span>
                    </div>
                </div>
                
                <div class="card-right">
                    <div class="inputs">
                        <div class="input-group">
                            <label for="jt-api-user-id" class="field-label">LinkedIn Email</label>
                            <input type="email" id="jt-api-user-id" placeholder="your@email.com" />
                        </div>
                    </div>
                    <button id="jt-save-btn" disabled>Add to Applications</button>
                </div>
            </div>
            <div class="card-footer-meta">
                <button id="jt-settings-btn" class="secondary-btn">Settings</button>
            </div>
            </div>
        `;
        shadow.appendChild(container);

        // UI Elements
        const userIdInput = shadow.getElementById('jt-api-user-id');
        const saveBtn = shadow.getElementById('jt-save-btn');
        const statusMsg = shadow.getElementById('jt-status-message');
        const identitySection = shadow.getElementById('jt-identity-info');
        const identityValue = shadow.getElementById('jt-identity-value');
        const settingsBtn = shadow.getElementById('jt-settings-btn');

        function setStatus(text, type = 'info') {
            statusMsg.textContent = text;
            statusMsg.setAttribute('data-variant', type);
        }

        settingsBtn.addEventListener('click', () => {
            chrome.runtime.sendMessage({ type: 'OPEN_OPTIONS' });
        });

        currentSettings = await getSettings();
        userIdInput.value = currentSettings.apiUserId || '';

        currentPageData = capturePageContent();

        if (currentPageData.linkedinHandle || currentPageData.linkedinMemberId) {
            identitySection.style.display = 'block';
            identityValue.textContent = currentPageData.linkedinHandle || `ID: ${currentPageData.linkedinMemberId}`;
        }

        if (userIdInput.value.trim()) {
            saveBtn.disabled = false;
        } else {
            setStatus('Email required', 'error');
        }

        // --- Events ---
        userIdInput.addEventListener('input', () => {
            if (userIdInput.value.trim()) {
                saveBtn.disabled = false;
                setStatus('Ready to track');
            } else {
                saveBtn.disabled = true;
                setStatus('Email required', 'error');
            }
        });

        saveBtn.addEventListener('click', async () => {
            const userId = userIdInput.value.trim();
            if (!userId) return;

            if (userId !== currentSettings.apiUserId) {
                chrome.storage.sync.set({ apiUserId: userId });
                currentSettings.apiUserId = userId;
            }

            saveBtn.disabled = true;
            setStatus('Saving...');

            const payload = {
                ...currentPageData,
                jobUrl: currentPageData.url,
                pageTitle: currentPageData.title,
                pageContent: currentPageData.fullText,
                userId: userId,
                notes: ''
            };

            chrome.runtime.sendMessage({ type: SAVE_EVENT, payload }, (response) => {
                saveBtn.disabled = false;
                if (response && response.success) {
                    setStatus('Saved! 🎉', 'success');
                } else {
                    setStatus('Failed', 'error');
                }
            });
        });
    }

    // Since LinkedIn is a Single Page App, we need to watch for URL/DOM shifts
    let lastUrl = location.href;
    const observer = new MutationObserver(() => {
        const url = location.href;
        if (url !== lastUrl) {
            lastUrl = url;
            setTimeout(injectCard, 1000); // Wait for page load
        } else if (!document.querySelector('#jt-card-host')) {
            // Also try to inject if content is missing
            injectCard();
        }
    });

    observer.observe(document.body, { subtree: true, childList: true });

    // Initial injection
    setTimeout(injectCard, 1500);
})();
