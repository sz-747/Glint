document.addEventListener('DOMContentLoaded', () => {
  const shell = document.querySelector('[data-dashboard-shell]');
  if (!shell) {
    return;
  }

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

  const textArea = shell.querySelector('[data-doc-content]');
  const wordCount = shell.querySelector('[data-word-count]');
  if (!textArea || !wordCount) {
    return;
  }

  textArea.addEventListener('input', () => {
    const words = textArea.value.trim().match(/\S+/g);
    wordCount.textContent = words ? String(words.length) : '0';
  });
});
