// Hamburger menu toggle for mobile navigation
document.addEventListener('DOMContentLoaded', () => {
  const hamburger = document.getElementById('hamburger');
  const navLinks = document.getElementById('nav-links');

  if (hamburger && navLinks) {
    hamburger.addEventListener('click', () => {
      const isOpen = navLinks.classList.toggle('active');
      hamburger.setAttribute('aria-expanded', String(isOpen));
    });

    // Close drawer when clicking anywhere outside the nav
    document.addEventListener('click', (event) => {
      if (!hamburger.contains(event.target) && !navLinks.contains(event.target)) {
        navLinks.classList.remove('active');
        hamburger.setAttribute('aria-expanded', 'false');
      }
    });
  }
});

document.addEventListener('DOMContentLoaded', () => {
  const shell = document.querySelector('[data-dashboard-shell]');
  if (!shell) {
    return;
  }

  // Panel collapse/expand toggles
  const panelToggles = shell.querySelectorAll('.panel-toggle');
  panelToggles.forEach((toggle) => {
    const target = toggle.dataset.target;
    const panel = shell.querySelector(`[data-panel="${target}"]`);
    if (!panel) {
      return;
    }

    toggle.addEventListener('click', () => {
      const collapsed = panel.classList.toggle('is-collapsed');
      shell.classList.toggle(`${target}-collapsed`, collapsed);
      toggle.setAttribute('aria-expanded', String(!collapsed));

      const arrow = toggle.querySelector('span');
      if (!arrow) {
        return;
      }

      if (target === 'left') {
        arrow.innerHTML = collapsed ? '&#9654;' : '&#9664;';
      } else if (target === 'right') {
        arrow.innerHTML = collapsed ? '&#9664;' : '&#9654;';
      }
    });
  });

  // Live word count
  const textArea = shell.querySelector('[data-doc-content]');
  const wordCount = shell.querySelector('[data-word-count]');
  if (!textArea || !wordCount) {
    return;
  }

  const updateWordCount = () => {
    const words = textArea.value.trim().match(/\S+/g);
    wordCount.textContent = words ? String(words.length) : '0';
  };

  textArea.addEventListener('input', updateWordCount);
  updateWordCount();
});
