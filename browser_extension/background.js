// Echo Protocol Browser Activity Monitor — Service Worker

const ECHO_API_URL = 'http://localhost:5000';
const TRIGGER_ID   = 1;   // Set to your browser_activity trigger ID
const REPORT_INTERVAL_MINUTES = 5;

let activeMinutes = 0;

// --- Alarm for periodic reporting ---
chrome.alarms.create('reportActivity', { periodInMinutes: REPORT_INTERVAL_MINUTES });

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'reportActivity') {
    reportActivity();
  }
});

// --- Messages from popup or content scripts ---
chrome.runtime.onMessage.addListener((message) => {
  if (message.type === 'activity') {
    activeMinutes += message.minutes || 1;
  }
});

// --- Navigation events are accessible in service workers ---
chrome.webNavigation.onCompleted.addListener(() => {
  activeMinutes++;
});

async function reportActivity() {
  if (activeMinutes === 0) return;

  try {
    const response = await fetch(
      `${ECHO_API_URL}/api/triggers/${TRIGGER_ID}/activity`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ minutes: activeMinutes }),
      }
    );

    if (response.ok) {
      console.log(`[Echo] Reported ${activeMinutes} active minute(s)`);
      activeMinutes = 0;
    } else {
      console.warn(`[Echo] Server returned ${response.status}`);
    }
  } catch (err) {
    console.error('[Echo] Failed to report activity:', err);
  }
}
