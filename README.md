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
