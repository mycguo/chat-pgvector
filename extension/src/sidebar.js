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
    const host = document.createElement('div');
    host.id = 'jt-sidebar-host';
    document.body.appendChild(host);

    const shadow = host.attachShadow({ mode: 'open' });

    // Inject Styles
    const styleLink = document.createElement('link');
    styleLink.rel = 'stylesheet';
    styleLink.href = chrome.runtime.getURL('src/sidebar.css');
    shadow.appendChild(styleLink);

    // Build HTML
    const container = document.createElement('div');
    container.id = 'jt-sidebar-container';
    container.innerHTML = `
        <button id="jt-close-btn" title="Close sidebar">&times;</button>
        <header>
            <img src="${chrome.runtime.getURL('assets/icons/icon48.png')}" alt="Logo" />
            <div>
                <h1>Job Tracker</h1>
                <p>Tracking your career move</p>
            </div>
        </header>
        <main>
            <section id="jt-page-info">
                <span class="label">Current Job</span>
                <p id="jt-page-title" class="value">Loading...</p>
                <p id="jt-page-url" class="value subtext"></p>
            </section>
            
            <section id="jt-identity-info" style="display: none;">
                <span class="label">Detected Identity</span>
                <p id="jt-identity-value" class="value"></p>
            </section>

            <section id="jt-user-info">
                <label class="label" for="jt-api-user-id">Account Email</label>
                <input type="email" id="jt-api-user-id" placeholder="your@email.com" />
            </section>

            <section id="jt-notes-section">
                <label class="label" for="jt-job-notes">Quick Notes</label>
                <textarea id="jt-job-notes" placeholder="Interview stage, referral, reminders..."></textarea>
            </section>
        </main>
        <footer>
            <button id="jt-save-btn" disabled>Add to Applications</button>
            <p id="jt-status-message">Ready to save.</p>
        </footer>
    `;
    shadow.appendChild(container);

    const toggleBtn = document.createElement('button');
    toggleBtn.id = 'jt-toggle-btn';
    toggleBtn.innerHTML = '🎯';
    toggleBtn.classList.add('hidden');
    shadow.appendChild(toggleBtn);

    // UI Elements
    const titleEl = shadow.getElementById('jt-page-title');
    const urlEl = shadow.getElementById('jt-page-url');
    const identitySection = shadow.getElementById('jt-identity-info');
    const identityValue = shadow.getElementById('jt-identity-value');
    const userIdInput = shadow.getElementById('jt-api-user-id');
    const notesEl = shadow.getElementById('jt-job-notes');
    const saveBtn = shadow.getElementById('jt-save-btn');
    const statusMsg = shadow.getElementById('jt-status-message');
    const closeBtn = shadow.getElementById('jt-close-btn');

    function setStatus(text, type = 'info') {
        statusMsg.textContent = text;
        statusMsg.setAttribute('data-variant', type);
    }

    async function init() {
        currentSettings = await getSettings();
        userIdInput.value = currentSettings.apiUserId || '';

        currentPageData = capturePageContent();
        titleEl.textContent = currentPageData.title || 'LinkedIn job page';
        urlEl.textContent = currentPageData.url || '';

        if (currentPageData.linkedinHandle || currentPageData.linkedinMemberId) {
            identitySection.style.display = 'block';
            identityValue.textContent = currentPageData.linkedinHandle || `ID: ${currentPageData.linkedinMemberId}`;
        }

        if (userIdInput.value.trim()) {
            saveBtn.disabled = false;
        } else {
            setStatus('Please set your email.', 'error');
        }

        // Auto-open
        container.classList.add('open');
    }

    // --- Events ---
    closeBtn.addEventListener('click', () => {
        container.classList.remove('open');
        toggleBtn.classList.remove('hidden');
    });

    toggleBtn.addEventListener('click', () => {
        container.classList.add('open');
        toggleBtn.classList.add('hidden');
    });

    userIdInput.addEventListener('input', () => {
        if (userIdInput.value.trim()) {
            saveBtn.disabled = false;
            setStatus('Ready to save.');
        } else {
            saveBtn.disabled = true;
            setStatus('Email is required.', 'error');
        }
    });

    saveBtn.addEventListener('click', async () => {
        const userId = userIdInput.value.trim();
        if (!userId) return;

        // Save email if changed
        if (userId !== currentSettings.apiUserId) {
            chrome.storage.sync.set({ apiUserId: userId });
            currentSettings.apiUserId = userId;
        }

        saveBtn.disabled = true;
        setStatus('Saving to Job Search...');

        const payload = {
            ...currentPageData,
            jobUrl: currentPageData.url,
            pageTitle: currentPageData.title,
            pageContent: currentPageData.fullText,
            userId: userId,
            notes: notesEl.value.trim()
        };

        chrome.runtime.sendMessage({ type: SAVE_EVENT, payload }, (response) => {
            saveBtn.disabled = false;
            if (response && response.success) {
                setStatus('Job added successfully! 🎉', 'success');
                notesEl.value = '';
                setTimeout(() => container.classList.remove('open'), 2000);
                setTimeout(() => toggleBtn.classList.remove('hidden'), 2000);
            } else {
                setStatus(response?.error || 'Failed to save.', 'error');
            }
        });
    });

    init();
})();
