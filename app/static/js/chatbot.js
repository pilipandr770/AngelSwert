const toggle = document.getElementById('chatToggle');
const panel = document.getElementById('chatPanel');
const closeBtn = document.getElementById('chatClose');
const form = document.getElementById('chatForm');
const input = document.getElementById('chatInput');
const messages = document.getElementById('chatMessages');
const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
const chatbotRoot = document.getElementById('chatbot');

const CHAT_DISMISS_UNTIL_KEY = 'as_chat_auto_open_dismiss_until';
const CHAT_GREETING_SHOWN_KEY = 'as_chat_greeting_shown';
const CHAT_SNOOZE_MS = 1000 * 60 * 60 * 8;
const DEFAULT_AUTO_OPEN_DELAY_MS = 1000 * 40;
const DEFAULT_GREETING_DE = 'Hallo und willkommen bei ASAI Studio. Ich kann Ihnen direkt freie Beratungstermine zeigen oder beim passenden Paket helfen.';

function parseEnabled(rawValue) {
  return ['1', 'true', 'yes', 'on'].includes((rawValue || '').toLowerCase());
}

function parseDelayMs(rawValue) {
  const n = Number(rawValue);
  if (!Number.isFinite(n)) return DEFAULT_AUTO_OPEN_DELAY_MS;
  const boundedSeconds = Math.max(5, Math.min(300, Math.floor(n)));
  return boundedSeconds * 1000;
}

const CHAT_AUTO_OPEN_ENABLED = false;
const CHAT_AUTO_OPEN_DELAY_MS = DEFAULT_AUTO_OPEN_DELAY_MS;
const CHAT_GREETING_TEXT = (chatbotRoot && chatbotRoot.dataset.greetingText ? chatbotRoot.dataset.greetingText.trim() : '') || DEFAULT_GREETING_DE;

let selectedSlot = null;

function saveChatIdentity(name, email) {
  if (typeof window === 'undefined' || !window.localStorage) return;
  const cleanName = (name || '').trim();
  const cleanEmail = (email || '').trim().toLowerCase();
  if (cleanName) {
    window.localStorage.setItem('as_chat_name', cleanName);
  }
  if (cleanEmail) {
    window.localStorage.setItem('as_chat_email', cleanEmail);
  }
}

function getChatIdentity() {
  const nameInput = document.getElementById('chatBookName');
  const emailInput = document.getElementById('chatBookEmail');
  const typedName = nameInput ? nameInput.value.trim() : '';
  const typedEmail = emailInput ? emailInput.value.trim().toLowerCase() : '';

  let savedName = '';
  let savedEmail = '';
  if (typeof window !== 'undefined' && window.localStorage) {
    savedName = (window.localStorage.getItem('as_chat_name') || '').trim();
    savedEmail = (window.localStorage.getItem('as_chat_email') || '').trim().toLowerCase();
  }

  return {
    name: typedName || savedName,
    email: typedEmail || savedEmail,
  };
}

function shouldSuppressAutoOpen() {
  if (typeof window === 'undefined' || !window.localStorage) return false;
  const raw = window.localStorage.getItem(CHAT_DISMISS_UNTIL_KEY) || '';
  const untilTs = Number(raw);
  return Number.isFinite(untilTs) && untilTs > Date.now();
}

function rememberDismiss() {
  if (typeof window === 'undefined' || !window.localStorage) return;
  window.localStorage.setItem(CHAT_DISMISS_UNTIL_KEY, String(Date.now() + CHAT_SNOOZE_MS));
}

function maybeShowGreeting() {
  if (!messages) return;
  const hasHistory = messages.children.length > 0;
  if (hasHistory) return;

  let alreadyShown = false;
  if (typeof window !== 'undefined' && window.localStorage) {
    alreadyShown = window.localStorage.getItem(CHAT_GREETING_SHOWN_KEY) === '1';
  }
  if (alreadyShown) return;

  addMessage('bot', CHAT_GREETING_TEXT);
  if (typeof window !== 'undefined' && window.localStorage) {
    window.localStorage.setItem(CHAT_GREETING_SHOWN_KEY, '1');
  }
}

function openPanel(options = {}) {
  const { isAuto = false } = options;
  if (!panel) return;
  panel.classList.remove('hidden');
  if (toggle) {
    toggle.classList.add('chatbot-toggle-hidden');
  }
  if (isAuto) {
    maybeShowGreeting();
  }
}

function closePanel() {
  if (!panel) return;
  panel.classList.add('hidden');
  if (toggle) {
    toggle.classList.remove('chatbot-toggle-hidden');
  }
  rememberDismiss();
}

if (toggle && panel) {
  toggle.addEventListener('click', () => openPanel({ isAuto: false }));
}

if (closeBtn) {
  closeBtn.addEventListener('click', closePanel);
}

function addMessage(role, text) {
  if (!messages) return;
  const row = document.createElement('div');
  row.className = `chat-row ${role}`;
  row.textContent = text;
  messages.appendChild(row);
  messages.scrollTop = messages.scrollHeight;
}

function recentHistoryPayload(limit = 12) {
  if (!messages) return [];
  const rows = Array.from(messages.querySelectorAll('.chat-row'));
  return rows.slice(-limit).map((row) => {
    const isUser = row.classList.contains('user');
    const isBot = row.classList.contains('bot');
    return {
      role: isUser ? 'user' : (isBot ? 'bot' : 'bot'),
      text: (row.textContent || '').trim(),
    };
  }).filter((item) => item.text);
}

function ensureBookingUi() {
  if (!panel) return;
  if (document.getElementById('chatCalendarControls')) return;

  const controls = document.createElement('div');
  controls.id = 'chatCalendarControls';
  controls.className = 'chat-calendar-controls';
  controls.innerHTML = `
    <button type="button" id="chatLoadSlotsBtn">Показати вільні слоти</button>
    <div id="chatSlotsContainer" class="chat-slots"></div>
    <div class="chat-booking-form">
      <input id="chatBookName" type="text" placeholder="Ваше ім'я">
      <input id="chatBookEmail" type="email" placeholder="Ваш email">
      <textarea id="chatBookNote" rows="2" placeholder="Коментар (необов'язково)"></textarea>
      <button type="button" id="chatBookBtn">Забронювати обраний слот</button>
    </div>
  `;
  panel.appendChild(controls);

}

async function loadSlots() {
  try {
    const response = await fetch(`/api/calendar/slots?days=90&timezone=${encodeURIComponent(userTimezone)}`);
    const data = await response.json();
    const container = document.getElementById('chatSlotsContainer');
    if (!container) return;

    container.innerHTML = '';
    const slots = Array.isArray(data.slots) ? data.slots.slice(0, 20) : [];
    if (!slots.length) {
      addMessage('bot', 'Поки немає вільних слотів у найближчі 3 місяці.');
      return;
    }

    addMessage('bot', `Время (${data.timezone || userTimezone}): ${data.now_local || data.now_utc}`);
    slots.forEach((slot) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'chat-slot-btn';
      btn.textContent = `${slot.starts_at_local || slot.starts_at} - ${slot.ends_at_local || slot.ends_at}`;
      btn.addEventListener('click', () => {
        selectedSlot = slot;
        addMessage('bot', `Обрано слот #${slot.id}`);
      });
      container.appendChild(btn);
    });
  } catch (error) {
    addMessage('bot', 'Не вдалося завантажити слоти календаря.');
  }
}

async function bookSelectedSlot() {
  const nameInput = document.getElementById('chatBookName');
  const emailInput = document.getElementById('chatBookEmail');
  const noteInput = document.getElementById('chatBookNote');

  const name = nameInput ? nameInput.value.trim() : '';
  const email = emailInput ? emailInput.value.trim() : '';
  const note = noteInput ? noteInput.value.trim() : '';

  if (!selectedSlot) {
    addMessage('bot', 'Спочатку оберіть слот.');
    return;
  }
  if (!name || !email) {
    addMessage('bot', 'Вкажіть ім\'я та email для бронювання.');
    return;
  }

  try {
    const response = await fetch('/api/calendar/book', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        slot_id: selectedSlot.id,
        name,
        email,
        note,
        timezone: userTimezone,
      }),
    });
    const data = await response.json();
    if (!response.ok) {
      addMessage('bot', data.error || 'Не вдалося забронювати слот.');
      return;
    }

    saveChatIdentity(name, email);
    addMessage('bot', `Готово! Бронювання #${data.booking_id} на ${data.slot.starts_at_local || data.slot.starts_at}`);
    selectedSlot = null;
  } catch (error) {
    addMessage('bot', 'Помилка під час бронювання. Спробуйте ще раз.');
  }
}

function bindBookingUi() {
  const showBookingBtn = document.getElementById('chatShowBookingBtn');
  const controls = document.getElementById('chatCalendarControls');
  const loadSlotsBtn = document.getElementById('chatLoadSlotsBtn');
  const bookBtn = document.getElementById('chatBookBtn');

  if (showBookingBtn && !showBookingBtn.dataset.bound) {
    showBookingBtn.addEventListener('click', async () => {
      if (controls) {
        const collapsed = controls.classList.contains('chat-calendar-collapsed');
        controls.classList.toggle('chat-calendar-collapsed', !collapsed);
        showBookingBtn.setAttribute('aria-expanded', collapsed ? 'true' : 'false');
        if (!collapsed) {
          return;
        }
      }
      await loadSlots();
    });
    showBookingBtn.dataset.bound = '1';
  }

  if (loadSlotsBtn && !loadSlotsBtn.dataset.bound) {
    loadSlotsBtn.addEventListener('click', loadSlots);
    loadSlotsBtn.dataset.bound = '1';
  }

  if (bookBtn && !bookBtn.dataset.bound) {
    bookBtn.addEventListener('click', bookSelectedSlot);
    bookBtn.dataset.bound = '1';
  }
}

ensureBookingUi();
bindBookingUi();

if (form) {
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const value = input.value.trim();
    if (!value) return;

    addMessage('user', value);
    input.value = '';

    try {
      const identity = getChatIdentity();
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: value,
          timezone: userTimezone,
          lead_name: identity.name,
          lead_email: identity.email,
          history: recentHistoryPayload(),
        })
      });
      const data = await response.json();
      addMessage('bot', data.reply || 'AI response error.');
    } catch (error) {
      addMessage('bot', 'Could not connect to AI service.');
    }
  });
}

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && panel && !panel.classList.contains('hidden')) {
    closePanel();
  }
});
