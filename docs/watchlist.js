(function () {
  const config = window.REDSTOCK_CONFIG || {};
  const fallbackStocks = Array.from(document.querySelectorAll('[data-stock-tag]'))
    .map((el) => el.textContent.trim())
    .filter(Boolean);

  const button = document.querySelector('[data-watchlist-open]');
  const modal = document.querySelector('[data-watchlist-modal]');
  const list = document.querySelector('[data-watchlist-list]');
  const addButton = document.querySelector('[data-watchlist-add]');
  const form = document.querySelector('[data-watchlist-form]');
  const closeButtons = document.querySelectorAll('[data-watchlist-close]');
  const status = document.querySelector('[data-watchlist-status]');
  const sheetLink = document.querySelector('[data-watchlist-sheet]');
  const timeInput = document.querySelector('[data-briefing-time]');
  const timeDisplay = document.querySelector('[data-briefing-time-display]');
  const stockTags = document.querySelector('[data-stock-tags]');

  const text = {
    placeholder: '\uc608: \uc0bc\uc131\uc804\uc790 \ub610\ub294 NVDA',
    remove: '\uc885\ubaa9 \uc0ad\uc81c',
    apiMissing: '\uc544\uc9c1 \uc800\uc7a5 API\uac00 \uc5f0\uacb0\ub418\uc9c0 \uc54a\uc558\uc2b5\ub2c8\ub2e4. \uc784\uc2dc\ub85c \ud604\uc7ac \ube0c\ub9ac\ud551 \uc885\ubaa9\uc744 \ubcf4\uc5ec\uc90d\ub2c8\ub2e4.',
    loadFailed: '\uc885\ubaa9 \ubaa9\ub85d\uc744 \ubd88\ub7ec\uc624\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4. \ud604\uc7ac \ube0c\ub9ac\ud551 \uc885\ubaa9\uc744 \ubcf4\uc5ec\uc90d\ub2c8\ub2e4.',
    needStock: '\uc885\ubaa9\uc744 \ud558\ub098 \uc774\uc0c1 \uc785\ub825\ud574\uc8fc\uc138\uc694.',
    apiNotConfigured: '\uc800\uc7a5 API URL\uc774 \uc544\uc9c1 \uc124\uc815\ub418\uc9c0 \uc54a\uc558\uc2b5\ub2c8\ub2e4.',
    saving: '\uc800\uc7a5 \uc911...',
    saved: '\uc800\uc7a5\ud588\uc2b5\ub2c8\ub2e4. \ub2e4\uc74c \ube0c\ub9ac\ud551\ubd80\ud130 \uc885\ubaa9\uacfc \uc2dc\uac04\uc774 \ubc18\uc601\ub429\ub2c8\ub2e4.',
    saveFailed: '\uc800\uc7a5\ud558\uc9c0 \ubabb\ud588\uc2b5\ub2c8\ub2e4. Google Apps Script \ubc30\ud3ec URL\uc744 \ud655\uc778\ud574\uc8fc\uc138\uc694.'
  };

  if (!button || !modal || !list || !addButton || !form || !status) return;
  if (sheetLink && config.sheetEditUrl) sheetLink.href = config.sheetEditUrl;

  function setStatus(message, tone) {
    status.textContent = message || '';
    status.dataset.tone = tone || '';
  }

  function updateVisibleSettings(stocks, briefingTime) {
    const cleanStocks = (stocks || []).map((stock) => String(stock).trim()).filter(Boolean);
    if (stockTags) {
      stockTags.innerHTML = '';
      cleanStocks.forEach((stock) => {
        const tag = document.createElement('span');
        tag.dataset.stockTag = '';
        tag.textContent = stock;
        stockTags.append(tag);
      });
    }
    if (timeDisplay && briefingTime) {
      timeDisplay.textContent = briefingTime;
    }
  }

  function collectStocks() {
    return Array.from(list.querySelectorAll('input'))
      .map((input) => input.value.trim())
      .filter(Boolean)
      .filter((value, index, array) => array.indexOf(value) === index);
  }

  function syncVisibleFromForm() {
    updateVisibleSettings(collectStocks(), timeInput && timeInput.value ? timeInput.value : '07:30');
  }

  function makeRow(value) {
    const row = document.createElement('div');
    row.className = 'watch-row';

    const input = document.createElement('input');
    input.type = 'text';
    input.name = 'stock';
    input.placeholder = text.placeholder;
    input.value = value || '';
    input.addEventListener('input', syncVisibleFromForm);

    const remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'icon-button';
    remove.setAttribute('aria-label', text.remove);
    remove.textContent = '-';
    remove.addEventListener('click', () => {
      if (list.children.length > 1) row.remove();
      else input.value = '';
      syncVisibleFromForm();
    });

    row.append(input, remove);
    return row;
  }

  function render(stocks) {
    list.innerHTML = '';
    const values = stocks.length ? stocks : [''];
    values.forEach((stock) => list.append(makeRow(stock)));
  }

  function loadStocksJsonp() {
    return new Promise((resolve, reject) => {
      const callbackName = `redstockWatchlist${Date.now()}`;
      const script = document.createElement('script');
      const separator = config.watchlistApiUrl.includes('?') ? '&' : '?';
      script.src = `${config.watchlistApiUrl}${separator}callback=${callbackName}`;
      script.async = true;
      const timeout = window.setTimeout(() => {
        cleanup();
        reject(new Error('watchlist timeout'));
      }, 12000);

      function cleanup() {
        window.clearTimeout(timeout);
        delete window[callbackName];
        script.remove();
      }

      window[callbackName] = (data) => {
        cleanup();
        resolve(data);
      };
      script.addEventListener('error', () => {
        cleanup();
        reject(new Error('watchlist load failed'));
      });
      document.head.append(script);
    });
  }

  async function loadStocks() {
    render(fallbackStocks);
    if (!config.watchlistApiUrl) {
      setStatus(text.apiMissing, 'warn');
      return;
    }
    try {
      const data = await loadStocksJsonp();
      const loadedStocks = Array.isArray(data.stocks) ? data.stocks : fallbackStocks;
      render(loadedStocks);
      if (timeInput && data.briefingTime) timeInput.value = data.briefingTime;
      updateVisibleSettings(loadedStocks, data.briefingTime);
      setStatus('', '');
    } catch (error) {
      setStatus(text.loadFailed, 'warn');
    }
  }

  function openModal() {
    modal.hidden = false;
    document.body.classList.add('modal-open');
    loadStocks();
    setTimeout(() => {
      const input = list.querySelector('input');
      if (input) input.focus();
    }, 0);
  }

  function closeModal() {
    modal.hidden = true;
    document.body.classList.remove('modal-open');
  }

  button.addEventListener('click', openModal);
  closeButtons.forEach((el) => el.addEventListener('click', closeModal));
  modal.addEventListener('click', (event) => {
    if (event.target === modal) closeModal();
  });
  addButton.addEventListener('click', () => {
    list.append(makeRow(''));
    list.lastElementChild.querySelector('input').focus();
    syncVisibleFromForm();
  });
  if (timeInput) timeInput.addEventListener('input', syncVisibleFromForm);

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const stocks = collectStocks();
    const briefingTime = timeInput && timeInput.value ? timeInput.value : '07:30';

    if (!stocks.length) {
      setStatus(text.needStock, 'warn');
      return;
    }
    if (!config.watchlistApiUrl) {
      setStatus(text.apiNotConfigured, 'error');
      return;
    }

    setStatus(text.saving, '');
    try {
      await fetch(config.watchlistApiUrl, {
        method: 'POST',
        mode: 'no-cors',
        headers: { 'Content-Type': 'text/plain;charset=utf-8' },
        body: JSON.stringify({ stocks, briefingTime })
      });
      updateVisibleSettings(stocks, briefingTime);
      setStatus(text.saved, 'ok');
    } catch (error) {
      setStatus(text.saveFailed, 'error');
    }
  });

  loadStocks();
})();
