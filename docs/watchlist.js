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

  if (!button || !modal || !list || !addButton || !form || !status) return;
  if (sheetLink && config.sheetEditUrl) sheetLink.href = config.sheetEditUrl;

  function setStatus(message, tone) {
    status.textContent = message || '';
    status.dataset.tone = tone || '';
  }

  function makeRow(value) {
    const row = document.createElement('div');
    row.className = 'watch-row';

    const input = document.createElement('input');
    input.type = 'text';
    input.name = 'stock';
    input.placeholder = '예: 삼성전자 또는 NVDA';
    input.value = value || '';

    const remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'icon-button';
    remove.setAttribute('aria-label', '종목 삭제');
    remove.textContent = '−';
    remove.addEventListener('click', () => {
      if (list.children.length > 1) row.remove();
      else input.value = '';
    });

    row.append(input, remove);
    return row;
  }

  function render(stocks) {
    list.innerHTML = '';
    const values = stocks.length ? stocks : [''];
    values.forEach((stock) => list.append(makeRow(stock)));
  }

  async function loadStocks() {
    render(fallbackStocks);
    if (!config.watchlistApiUrl) {
      setStatus('아직 저장 API가 연결되지 않았습니다. 임시로 현재 브리핑 종목을 보여줍니다.', 'warn');
      return;
    }
    try {
      const data = await loadStocksJsonp();
      render(Array.isArray(data.stocks) ? data.stocks : fallbackStocks);
      setStatus('', '');
    } catch (error) {
      setStatus('종목 목록을 불러오지 못했습니다. 현재 브리핑 종목을 보여줍니다.', 'warn');
    }
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
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const stocks = Array.from(list.querySelectorAll('input'))
      .map((input) => input.value.trim())
      .filter(Boolean)
      .filter((value, index, array) => array.indexOf(value) === index);

    if (!stocks.length) {
      setStatus('종목을 하나 이상 입력해주세요.', 'warn');
      return;
    }
    if (!config.watchlistApiUrl) {
      setStatus('저장 API URL이 아직 설정되지 않았습니다. README의 Apps Script 연결 단계를 완료해주세요.', 'error');
      return;
    }

    setStatus('저장 중...', '');
    try {
      await fetch(config.watchlistApiUrl, {
        method: 'POST',
        mode: 'no-cors',
        headers: { 'Content-Type': 'text/plain;charset=utf-8' },
        body: JSON.stringify({ stocks })
      });
      setStatus('저장 요청을 보냈습니다. 다음 브리핑부터 반영됩니다.', 'ok');
    } catch (error) {
      setStatus('저장하지 못했습니다. Google Apps Script 배포 URL을 확인해주세요.', 'error');
    }
  });
})();
