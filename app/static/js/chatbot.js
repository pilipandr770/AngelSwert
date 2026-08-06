const toggle = document.getElementById('chatToggle');
const panel = document.getElementById('chatPanel');
const closeBtn = document.getElementById('chatClose');
const form = document.getElementById('chatForm');
const input = document.getElementById('chatInput');
const messages = document.getElementById('chatMessages');
const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';

let selectedSlot = null;

function openPanel() {
  if (!panel) return;
  panel.classList.remove('hidden');
  if (toggle) {
    toggle.classList.add('chatbot-toggle-hidden');
  }
}

function closePanel() {
  if (!panel) return;
  panel.classList.add('hidden');
  if (toggle) {
    toggle.classList.remove('chatbot-toggle-hidden');
  }
}

if (toggle && panel) {
  toggle.addEventListener('click', openPanel);
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
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: value, timezone: userTimezone })
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
