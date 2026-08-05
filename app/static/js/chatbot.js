const toggle = document.getElementById('chatToggle');
const panel = document.getElementById('chatPanel');
const form = document.getElementById('chatForm');
const input = document.getElementById('chatInput');
const messages = document.getElementById('chatMessages');

if (toggle && panel) {
  toggle.addEventListener('click', () => panel.classList.toggle('hidden'));
}

function addMessage(role, text) {
  if (!messages) return;
  const row = document.createElement('div');
  row.className = `chat-row ${role}`;
  row.textContent = text;
  messages.appendChild(row);
  messages.scrollTop = messages.scrollHeight;
}

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
        body: JSON.stringify({ message: value })
      });
      const data = await response.json();
      addMessage('bot', data.reply || 'AI response error.');
    } catch (error) {
      addMessage('bot', 'Could not connect to AI service.');
    }
  });
}
