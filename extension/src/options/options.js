/* global getExtensionSettings, saveExtensionSettings, DEFAULT_EXTENSION_SETTINGS */
const form = document.getElementById('settings-form');
const endpointInput = document.getElementById('api-endpoint');
const apiKeyInput = document.getElementById('api-key');
const sourceLabelInput = document.getElementById('source-label');
const statusEl = document.getElementById('settings-status');

async function loadSettings() {
    const settings = await getExtensionSettings();
    endpointInput.value = settings.apiEndpoint || DEFAULT_EXTENSION_SETTINGS.apiEndpoint;
    apiKeyInput.value = settings.apiKey || '';
    sourceLabelInput.value = settings.sourceLabel || DEFAULT_EXTENSION_SETTINGS.sourceLabel;
}

function showStatus(message, type = 'info') {
    statusEl.textContent = message;
    statusEl.dataset.variant = type;
}

form.addEventListener('submit', async (event) => {
    event.preventDefault();
    showStatus('Saving settings...');

    try {
        await saveExtensionSettings({
            apiEndpoint: endpointInput.value.trim() || DEFAULT_EXTENSION_SETTINGS.apiEndpoint,
            apiKey: apiKeyInput.value.trim(),
            sourceLabel: sourceLabelInput.value.trim() || DEFAULT_EXTENSION_SETTINGS.sourceLabel
        });
        showStatus('Settings saved successfully.', 'success');
    } catch (error) {
        console.error('Job Collector: unable to save settings', error);
        showStatus('Failed to save settings. Check console for details.', 'error');
    }
});

document.addEventListener('DOMContentLoaded', loadSettings);
