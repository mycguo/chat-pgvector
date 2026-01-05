(function () {
    const DEFAULT_SETTINGS = {
        apiEndpoint: "http://localhost:8501/api/jobs",
        apiKey: "",
        sourceLabel: "linkedin-job-page"
    };

    const CONFIG = Object.freeze({
        defaultIntakeUrl: DEFAULT_SETTINGS.apiEndpoint,
        storageKey: "jobCollectorSettings",
        metadataVersion: 1
    });

    function hasSyncStorage() {
        return Boolean(globalThis.chrome && chrome.storage && chrome.storage.sync);
    }

    function getSettings() {
        return new Promise((resolve) => {
            if (!hasSyncStorage()) {
                resolve({ ...DEFAULT_SETTINGS });
                return;
            }

            chrome.storage.sync.get(DEFAULT_SETTINGS, (stored) => {
                if (chrome.runtime && chrome.runtime.lastError) {
                    console.warn("Job Collector: storage read failed", chrome.runtime.lastError);
                    resolve({ ...DEFAULT_SETTINGS });
                    return;
                }

                resolve({ ...DEFAULT_SETTINGS, ...stored });
            });
        });
    }

    function saveSettings(updates) {
        return new Promise((resolve, reject) => {
            if (!hasSyncStorage()) {
                reject(new Error("Chrome storage is unavailable"));
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

    globalThis.EXTENSION_CONFIG = CONFIG;
    globalThis.getExtensionSettings = getSettings;
    globalThis.saveExtensionSettings = saveSettings;
    globalThis.DEFAULT_EXTENSION_SETTINGS = DEFAULT_SETTINGS;
})();
