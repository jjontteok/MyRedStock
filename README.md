# RedStock Kakao Briefing

Google Sheets의 종목 목록을 읽고, 매일 아침 KakaoTalk 나와의 채팅방으로 주식 뉴스 브리핑 링크를 보내는 GitHub Actions 프로젝트입니다. 전체 브리핑은 GitHub Pages HTML 페이지로 발행됩니다.

## 동작 구조

```text
Google Sheets A열
  -> GitHub Actions schedule
  -> Google News RSS 수집
  -> OpenAI 요약
  -> GitHub Pages 브리핑 페이지 생성
  -> KakaoTalk 나에게 보내기로 링크 발송
```

## Google Sheets 형식

A열에 한 줄에 하나씩 종목을 적습니다.

```text
삼성전자 005930.KS
SK하이닉스 000660.KS
NVIDIA NVDA
Tesla TSLA
```

시트 공유 권한은 `링크가 있는 모든 사용자: 보기 가능`이어야 합니다.

## GitHub 설정

1. 새 GitHub repository를 만듭니다.
2. 이 폴더의 파일을 repository 루트에 올립니다.
3. GitHub repository에서 `Settings -> Secrets and variables -> Actions -> Secrets`로 이동합니다.
4. 아래 secrets를 추가합니다.

```text
GOOGLE_SHEET_CSV_URL
KAKAO_REST_API_KEY
KAKAO_REFRESH_TOKEN
OPENAI_API_KEY
```

`GOOGLE_SHEET_CSV_URL` 값:

```text
https://docs.google.com/spreadsheets/d/1yC36MDsTswSkwLbZe5OwwGdjw2ViVcN0vpC1AzBXNY0/export?format=csv&gid=0
```

`KAKAO_REST_API_KEY`는 Kakao Developers의 REST API 키입니다.

`KAKAO_REFRESH_TOKEN`은 Kakao OAuth로 발급받은 refresh token입니다. 비밀번호처럼 취급하세요.

`OPENAI_API_KEY`는 OpenAI API 키입니다.

5. `Settings -> Pages`로 이동합니다.
6. `Build and deployment`에서 `Deploy from a branch`를 선택합니다.
7. Branch는 `main`, 폴더는 `/docs`로 설정합니다.
8. 저장 후 표시되는 GitHub Pages 주소를 복사합니다.
9. `Settings -> Secrets and variables -> Actions -> Variables`에서 아래 variable을 추가합니다.

```text
PUBLIC_BRIEFING_URL
```

값은 GitHub Pages 주소입니다. 예:

```text
https://YOUR_GITHUB_ID.github.io/YOUR_REPOSITORY_NAME/
```

Kakao Developers에서 링크 버튼이 열리지 않으면 `앱 -> 제품 링크`에 위 GitHub Pages 도메인을 Web domain으로 추가하세요.
버튼이 표시되지 않는 카카오톡 환경을 대비해 메시지 본문에도 브리핑 URL을 함께 넣습니다.

## 실행 시간

`.github/workflows/daily-briefing.yml`은 UTC 기준 `22:30`에 실행됩니다. 한국시간으로는 매일 오전 `07:30`입니다.

수동 테스트는 GitHub repository의 `Actions -> Daily stock Kakao briefing -> Run workflow`에서 실행할 수 있습니다.

## 카카오톡 메시지

카카오톡에는 짧은 도착 알림과 브리핑 페이지 버튼만 보냅니다. 전체 요약, 종목별 내용, 출처 링크는 GitHub Pages에서 확인합니다.

## 관심 종목 설정 UI

브리핑 페이지의 `주식 종목 설정하기` 버튼은 `docs/watchlist.js`에서 동작합니다. 정적 GitHub Pages는 Google Sheets에 직접 쓸 수 없으므로, Google Apps Script 웹앱을 중간 저장 API로 사용합니다.

1. Google Sheet를 엽니다.
2. `확장 프로그램 -> Apps Script`를 엽니다.
3. `apps-script/Code.gs` 내용을 Apps Script 편집기에 붙여넣습니다.
4. `SHEET_NAME`이 실제 시트 이름과 다르면 수정합니다.
5. `배포 -> 새 배포 -> 웹 앱`을 선택합니다.
6. 실행 권한은 본인, 액세스 권한은 `모든 사용자`로 설정합니다.
7. 배포 후 Web App URL을 복사합니다.
8. `docs/config.js`의 `watchlistApiUrl`에 Web App URL을 넣고 commit/push합니다.

연결 전에는 페이지에서 현재 브리핑 종목을 보여주지만, 제출 저장은 동작하지 않습니다. 연결 후에는 입력/추가/삭제와 발송 시간 변경 후 `제출하기`를 누르면 Google Sheets A열과 발송 시간이 갱신되고 다음 브리핑부터 반영됩니다.

GitHub Actions는 10분마다 깨어난 뒤 Apps Script의 `briefingTime` 값을 확인합니다. 설정한 한국시간 기준 발송 시각과 맞을 때만 카카오톡 브리핑을 보냅니다.

### Apps Script 카카오 알림 트리거

GitHub Actions 스케줄이 지연되거나 누락되는 경우를 대비해 Apps Script에서도 10분마다 설정 시간을 확인하고 카카오톡 링크 알림을 보낼 수 있습니다.

Apps Script의 `프로젝트 설정 -> 스크립트 속성`에 아래 값을 추가합니다.

```text
KAKAO_REST_API_KEY
KAKAO_REFRESH_TOKEN
```

그다음 Apps Script 편집기에서 `setupRedStockTrigger()`를 한 번 실행합니다. 테스트 발송은 `testSendKakaoNow()`로 확인할 수 있습니다.

## 로컬 테스트

`.env.example`을 참고해 환경 변수를 설정한 뒤 실행합니다.

```powershell
pip install -r requirements.txt
python send_briefing.py
```

PowerShell 예시:

```powershell
$env:GOOGLE_SHEET_CSV_URL="https://docs.google.com/spreadsheets/d/1yC36MDsTswSkwLbZe5OwwGdjw2ViVcN0vpC1AzBXNY0/export?format=csv&gid=0"
$env:KAKAO_REST_API_KEY="..."
$env:KAKAO_REFRESH_TOKEN="..."
$env:OPENAI_API_KEY="..."
python send_briefing.py
```
