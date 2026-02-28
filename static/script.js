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

function togglePassword(inputId, button) {
  const input = document.getElementById(inputId);
  if (input.type === 'password') {
    input.type = 'text';
    button.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>';
  } else {
    input.type = 'password';
    button.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>';
  }
}
