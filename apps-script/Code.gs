const SHEET_NAME = 'Sheet1';

function doGet() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME)
    || SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
  const values = sheet.getRange(1, 1, Math.max(sheet.getLastRow(), 1), 1)
    .getValues()
    .flat()
    .map(value => String(value).trim())
    .filter(value => value && !value.startsWith('#'));

  return ContentService
    .createTextOutput(JSON.stringify({ ok: true, stocks: values }))
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

  return ContentService
    .createTextOutput(JSON.stringify({ ok: true, stocks: cleaned }))
    .setMimeType(ContentService.MimeType.JSON);
}
