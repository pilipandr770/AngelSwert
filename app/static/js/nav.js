const navToggle = document.getElementById('navToggle');
const siteNavMobile = document.getElementById('siteNavMobile');

if (navToggle && siteNavMobile) {
  navToggle.addEventListener('click', () => {
    const isOpen = siteNavMobile.classList.toggle('open');
    navToggle.setAttribute('aria-expanded', String(isOpen));
  });

  siteNavMobile.querySelectorAll('a').forEach((link) => {
    link.addEventListener('click', () => {
      siteNavMobile.classList.remove('open');
      navToggle.setAttribute('aria-expanded', 'false');
    });
  });
}
