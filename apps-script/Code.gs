const SHEET_NAME = 'Sheet1';
const DEFAULT_BRIEFING_TIME = '07:30';
const BRIEFING_PAGE_URL = 'https://jjontteok.github.io/MyRedStock/';
const KAKAO_TOKEN_URL = 'https://kauth.kakao.com/oauth/token';
const KAKAO_MEMO_URL = 'https://kapi.kakao.com/v2/api/talk/memo/default/send';

function getBriefingTime_() {
  return PropertiesService.getScriptProperties().getProperty('BRIEFING_TIME') || DEFAULT_BRIEFING_TIME;
}

function setBriefingTime_(value) {
  const time = String(value || '').trim();
  if (!/^\d{2}:\d{2}$/.test(time)) return getBriefingTime_();
  const parts = time.split(':').map(Number);
  if (parts[0] > 23 || parts[1] > 59) return getBriefingTime_();
  PropertiesService.getScriptProperties().setProperty('BRIEFING_TIME', time);
  return time;
}

function doGet(e) {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME)
    || SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
  const values = sheet.getRange(1, 1, Math.max(sheet.getLastRow(), 1), 1)
    .getValues()
    .flat()
    .map(value => String(value).trim())
    .filter(value => value && !value.startsWith('#'));

  const callback = e && e.parameter && e.parameter.callback;
  const props = PropertiesService.getScriptProperties();
  const triggerCount = ScriptApp.getProjectTriggers()
    .filter(trigger => trigger.getHandlerFunction() === 'checkAndSendKakao')
    .length;
  const body = JSON.stringify({
    ok: true,
    stocks: values,
    briefingTime: getBriefingTime_(),
    diagnostics: {
      hasKakaoRestApiKey: Boolean(props.getProperty('KAKAO_REST_API_KEY')),
      hasKakaoRefreshToken: Boolean(props.getProperty('KAKAO_REFRESH_TOKEN')),
      triggerCount,
      lastSentKey: props.getProperty('LAST_SENT_KEY') || '',
      lastCheckedAt: props.getProperty('LAST_CHECKED_AT') || '',
      lastError: props.getProperty('LAST_ERROR') || '',
    },
  });
  if (callback) {
    return ContentService
      .createTextOutput(`${callback}(${body});`)
      .setMimeType(ContentService.MimeType.JAVASCRIPT);
  }

  return ContentService
    .createTextOutput(body)
    .setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  const payload = JSON.parse(e.postData.contents || '{}');
  const stocks = Array.isArray(payload.stocks) ? payload.stocks : [];
  const cleaned = stocks
    .map(value => String(value).trim())
    .filter(Boolean)
    .filter((value, index, array) => array.indexOf(value) === index);

  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME)
    || SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
  sheet.clearContents();
  if (cleaned.length > 0) {
    sheet.getRange(1, 1, cleaned.length, 1).setValues(cleaned.map(value => [value]));
  }
  const briefingTime = setBriefingTime_(payload.briefingTime);

  return ContentService
    .createTextOutput(JSON.stringify({ ok: true, stocks: cleaned, briefingTime }))
    .setMimeType(ContentService.MimeType.JSON);
}

function setupRedStockTrigger() {
  ScriptApp.getProjectTriggers()
    .filter(trigger => trigger.getHandlerFunction() === 'checkAndSendKakao')
    .forEach(trigger => ScriptApp.deleteTrigger(trigger));

  ScriptApp.newTrigger('checkAndSendKakao')
    .timeBased()
    .everyMinutes(1)
    .create();
}

function checkAndSendKakao() {
  const props = PropertiesService.getScriptProperties();
  props.setProperty('LAST_CHECKED_AT', Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd HH:mm:ss'));
  try {
    const now = new Date();
    const date = Utilities.formatDate(now, 'Asia/Seoul', 'yyyy-MM-dd');
    const currentTime = Utilities.formatDate(now, 'Asia/Seoul', 'HH:mm');
    const targetTime = getBriefingTime_();

    if (!isWithinSendWindow_(currentTime, targetTime, 30)) return;

    const sentKey = `${date}-${targetTime}`;
    if (props.getProperty('LAST_SENT_KEY') === sentKey) return;

    sendKakaoBriefingLink_(date, targetTime);
    props.setProperty('LAST_SENT_KEY', sentKey);
    props.deleteProperty('LAST_ERROR');
  } catch (error) {
    props.setProperty('LAST_ERROR', `${error && error.message ? error.message : error}`);
    throw error;
  }
}

function testSendKakaoNow() {
  const now = new Date();
  const date = Utilities.formatDate(now, 'Asia/Seoul', 'yyyy-MM-dd');
  sendKakaoBriefingLink_(date, getBriefingTime_());
}

function isWithinSendWindow_(currentTime, targetTime, windowMinutes) {
  const current = toMinutes_(currentTime);
  const target = toMinutes_(targetTime);
  return current >= target && current < target + windowMinutes;
}

function toMinutes_(time) {
  const parts = String(time).split(':').map(Number);
  return parts[0] * 60 + parts[1];
}

function sendKakaoBriefingLink_(date, targetTime) {
  const props = PropertiesService.getScriptProperties();
  const restApiKey = props.getProperty('KAKAO_REST_API_KEY');
  const refreshToken = props.getProperty('KAKAO_REFRESH_TOKEN');
  if (!restApiKey || !refreshToken) {
    throw new Error('Missing KAKAO_REST_API_KEY or KAKAO_REFRESH_TOKEN script property.');
  }

  const tokenResponse = UrlFetchApp.fetch(KAKAO_TOKEN_URL, {
    method: 'post',
    payload: {
      grant_type: 'refresh_token',
      client_id: restApiKey,
      refresh_token: refreshToken,
    },
    muteHttpExceptions: false,
  });
  const token = JSON.parse(tokenResponse.getContentText()).access_token;
  const url = `${BRIEFING_PAGE_URL}briefings/${date}.html?v=${Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyyMMddHHmmss')}`;
  const template = {
    object_type: 'text',
    text: `RedStock 브리핑 알림\n설정 시간: ${targetTime}\n${url}`,
    link: {
      web_url: url,
      mobile_web_url: url,
    },
    buttons: [
      {
        title: '브리핑 보기',
        link: {
          web_url: url,
          mobile_web_url: url,
        },
      },
    ],
  };

  UrlFetchApp.fetch(KAKAO_MEMO_URL, {
    method: 'post',
    headers: {
      Authorization: `Bearer ${token}`,
    },
    payload: {
      template_object: JSON.stringify(template),
    },
    muteHttpExceptions: false,
  });
}
