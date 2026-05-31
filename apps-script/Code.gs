const SHEET_NAME = 'Sheet1';
const DEFAULT_BRIEFING_TIME = '07:30';

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
  const body = JSON.stringify({ ok: true, stocks: values, briefingTime: getBriefingTime_() });
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
