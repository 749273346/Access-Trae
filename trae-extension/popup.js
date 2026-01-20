document.addEventListener('DOMContentLoaded', restoreOptions);
document.getElementById('saveBtn').addEventListener('click', saveOptions);
document.getElementById('mode').addEventListener('change', toggleAiSettings);
document.getElementById('shortcutLink').addEventListener('click', () => {
  chrome.tabs.create({ url: 'chrome://extensions/shortcuts' });
});

const DEFAULT_SERVER_URL = "http://127.0.0.1:18000";

function normalizeServerUrl(serverUrl) {
  return (serverUrl || DEFAULT_SERVER_URL).trim().replace(/\/+$/, '');
}

function toggleAiSettings() {
  const mode = document.getElementById('mode').value;
  const aiSettings = document.getElementById('ai-settings');
  if (mode === 'ai_rewrite') {
    aiSettings.classList.remove('hidden');
  } else {
    aiSettings.classList.add('hidden');
  }
}

function saveOptions() {
  const mode = document.getElementById('mode').value;
  const model = document.getElementById('model').value;
  const apiKey = document.getElementById('apiKey').value;
  const baseUrl = document.getElementById('baseUrl').value;
  const savePath = document.getElementById('savePath').value;
  const backendUrl = document.getElementById('backendUrl').value.trim().replace(/\/+$/, '');

  chrome.storage.local.set({
    mode: mode,
    model: model,
    apiKey: apiKey,
    baseUrl: baseUrl,
    savePath: savePath,
    backendUrl: backendUrl || DEFAULT_SERVER_URL
  }, function() {
    const status = document.getElementById('statusText');
    status.textContent = 'Settings saved.';
    setTimeout(function() {
      checkServer(backendUrl || DEFAULT_SERVER_URL);
    }, 750);
  });
}

function restoreOptions() {
  chrome.storage.local.get({
    mode: 'raw',
    model: 'gpt-3.5-turbo',
    apiKey: '',
    baseUrl: '',
    savePath: '',
    backendUrl: DEFAULT_SERVER_URL
  }, function(items) {
    document.getElementById('mode').value = items.mode;
    document.getElementById('model').value = items.model;
    document.getElementById('apiKey').value = items.apiKey;
    document.getElementById('baseUrl').value = items.baseUrl;
    document.getElementById('savePath').value = items.savePath;
    document.getElementById('backendUrl').value = (items.backendUrl || DEFAULT_SERVER_URL).replace(/\/+$/, '');
    
    toggleAiSettings();
    checkServer(items.backendUrl || DEFAULT_SERVER_URL);
  });
}

function checkServer(serverUrl) {
  const indicator = document.getElementById('indicator');
  const statusText = document.getElementById('statusText');

  const normalized = normalizeServerUrl(serverUrl);
  indicator.className = 'indicator';
  statusText.textContent = 'Checking connection...';

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 1500);

  fetch(`${normalized}/health`, { signal: controller.signal, cache: 'no-store' })
    .then(response => {
      if (response.ok) {
        indicator.className = 'indicator connected';
        statusText.textContent = 'Trae Server Connected';
      } else {
        throw new Error('Server error');
      }
    })
    .catch(() => {
      indicator.className = 'indicator error';
      statusText.textContent = 'Disconnected (Run server.py)';
    })
    .finally(() => clearTimeout(timeoutId));
}
