(function () {
  const COOKIE_NAME = 'as_cookie_consent';
  const MAX_AGE_SECONDS = 60 * 60 * 24 * 180;

  const banner = document.getElementById('cookieBanner');
  const modal = document.getElementById('cookieSettingsModal');
  const manageBtn = document.getElementById('cookieManageBtn');
  const analyticsOptIn = document.getElementById('cookieAnalyticsOptIn');

  function setCookie(value) {
    document.cookie = `${COOKIE_NAME}=${encodeURIComponent(value)}; Max-Age=${MAX_AGE_SECONDS}; Path=/; SameSite=Lax`;
  }

  function getCookie() {
    const prefix = `${COOKIE_NAME}=`;
    const parts = document.cookie.split(';').map((v) => v.trim());
    for (const item of parts) {
      if (item.startsWith(prefix)) {
        return decodeURIComponent(item.slice(prefix.length));
      }
    }
    return '';
  }

  function hasConsent() {
    return getCookie() === 'all';
  }

  function hasDecision() {
    const value = getCookie();
    return value === 'all' || value === 'essential';
  }

  function showBanner() {
    if (!banner) return;
    banner.classList.remove('hidden');
  }

  function hideBanner() {
    if (!banner) return;
    banner.classList.add('hidden');
  }

  function openSettings() {
    if (!modal) return;
    if (analyticsOptIn) {
      analyticsOptIn.checked = hasConsent();
    }
    modal.classList.remove('hidden');
    modal.setAttribute('aria-hidden', 'false');
  }

  function closeSettings() {
    if (!modal) return;
    modal.classList.add('hidden');
    modal.setAttribute('aria-hidden', 'true');
  }

  function applyConsent(value) {
    setCookie(value);
    hideBanner();
    closeSettings();
    if (manageBtn) {
      manageBtn.classList.remove('hidden');
    }
  }

  window.ASConsent = {
    canTrackAnalytics: hasConsent,
    getValue: getCookie,
    openSettings,
  };

  const acceptAll = document.getElementById('cookieAcceptAll');
  const rejectOptional = document.getElementById('cookieRejectOptional');
  const openSettingsBtn = document.getElementById('cookieOpenSettings');
  const closeSettingsBtn = document.getElementById('cookieCloseSettings');
  const saveSettings = document.getElementById('cookieSaveSettings');

  if (acceptAll) {
    acceptAll.addEventListener('click', () => applyConsent('all'));
  }

  if (rejectOptional) {
    rejectOptional.addEventListener('click', () => applyConsent('essential'));
  }

  if (openSettingsBtn) {
    openSettingsBtn.addEventListener('click', openSettings);
  }

  if (closeSettingsBtn) {
    closeSettingsBtn.addEventListener('click', closeSettings);
  }

  if (saveSettings) {
    saveSettings.addEventListener('click', () => {
      const value = analyticsOptIn && analyticsOptIn.checked ? 'all' : 'essential';
      applyConsent(value);
    });
  }

  if (modal) {
    modal.addEventListener('click', (event) => {
      const target = event.target;
      if (target instanceof HTMLElement && target.dataset.cookieClose === '1') {
        closeSettings();
      }
    });
  }

  if (manageBtn) {
    manageBtn.addEventListener('click', openSettings);
  }

  if (!hasDecision()) {
    showBanner();
  } else if (manageBtn) {
    manageBtn.classList.remove('hidden');
  }
})();
