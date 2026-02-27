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
  const editorForm = shell.querySelector('.editor-form');
  const ghostBox = shell.querySelector('[data-ghost-suggestion]');
  const ghostText = shell.querySelector('[data-ghost-text]');
  if (!textArea || !wordCount) {
    return;
  }

  const currentDocId = editorForm ? editorForm.dataset.docId : null;
  const suggestionState = {
    quoteId: null,
    analysisChunkId: null,
    text: '',
    score: null,
    matchType: null,
  };

  let debounceTimer = null;
  let activeRequest = null;
  let lastShownLogKey = '';

    const updateWordCount = () => {
    const words = textArea.value.trim().match(/\S+/g);
      wordCount.textContent = words ? String(words.length) : '0';
    };

  const clearSuggestion = () => {
    suggestionState.quoteId = null;
    suggestionState.analysisChunkId = null;
    suggestionState.text = '';
    suggestionState.score = null;
    suggestionState.matchType = null;
    if (ghostText) {
      ghostText.textContent = '';
        }
    if (ghostBox) {
      ghostBox.hidden = true;
    }
  };

  const showSuggestion = (payload) => {
    const suggestion = typeof payload.suggestion === 'string' ? payload.suggestion.trim() : '';
    if (!suggestion || !ghostBox || !ghostText) {
      clearSuggestion();
      return;
    }

    suggestionState.quoteId = payload.quote_id ?? null;
    suggestionState.analysisChunkId = payload.analysis_chunk_id ?? null;
    suggestionState.text = suggestion;
    suggestionState.score = payload.score ?? null;
    suggestionState.matchType = payload.match_type ?? null;

    ghostText.textContent = suggestion;
    ghostBox.hidden = false;
  };

  const logSuggestion = (accepted) => {
    if (!suggestionState.quoteId && !suggestionState.analysisChunkId) {
      return;
    }

    fetch('/api/log-suggestion', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        quote_id: suggestionState.quoteId,
        analysis_chunk_id: suggestionState.analysisChunkId,
        typed_context: textArea.value.slice(-220),
        accepted,
      }),
    }).catch(() => {});
  };

  const fetchSuggestion = async () => {
    if (activeRequest) {
      activeRequest.abort();
    }
    activeRequest = new AbortController();

    try {
      const response = await fetch('/api/suggest-analysis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: activeRequest.signal,
        body: JSON.stringify({
          text: textArea.value,
          document_id: currentDocId ? Number(currentDocId) : null,
        }),
      });

      if (!response.ok) {
        clearSuggestion();
        return;
      }

      const payload = await response.json();
      showSuggestion(payload);

      if (payload.suggestion) {
        const key = `${payload.quote_id || 'none'}:${payload.analysis_chunk_id || 'none'}:${payload.match_type || 'none'}`;
        if (key !== lastShownLogKey) {
          lastShownLogKey = key;
          logSuggestion(false);
        }
      } else {
        lastShownLogKey = '';
      }
    } catch (error) {
      if (error.name !== 'AbortError') {
        clearSuggestion();
      }
    }
  };

  const scheduleSuggestionFetch = () => {
    if (debounceTimer) {
      window.clearTimeout(debounceTimer);
    }
    debounceTimer = window.setTimeout(fetchSuggestion, 160);
  };

  textArea.addEventListener('input', () => {
    updateWordCount();
    scheduleSuggestionFetch();
  });

  textArea.addEventListener('keydown', (event) => {
    if (event.key === 'Tab' && suggestionState.text) {
      event.preventDefault();
      const needsSpace = textArea.value.length > 0 && !/\s$/.test(textArea.value);
      textArea.value = `${textArea.value}${needsSpace ? ' ' : ''}${suggestionState.text}`;
      updateWordCount();
      logSuggestion(true);
      clearSuggestion();
      return;
    }

    if (event.key === 'Escape' && suggestionState.text) {
      event.preventDefault();
      clearSuggestion();
    }
  });

  updateWordCount();
});
