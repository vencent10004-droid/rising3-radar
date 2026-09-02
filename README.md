# 삼법형 레이더 (Rising Three Methods Radar)

코스피·코스닥 전종목에서 **상승 삼법형** 캔들 패턴을 매일 스크리닝해 보여주는 설치형 웹앱(PWA)입니다.

- **앱**: https://vencent10004-droid.github.io/rising3-radar/
  - 크롬에서 열고 메뉴(⋮) → "앱 설치" 또는 "홈 화면에 추가"
- **자동 갱신**: 평일 장 마감 후 스크리닝 결과가 `data/`에 커밋되면 1~2분 내 앱에 반영

## 패턴 기준

| 구분 | 조건 |
|---|---|
| 완성형 (A) | 장대양봉(몸통 1.5%+) → 소음봉 3개(몸통이 첫 양봉보다 작고, 종가 하락 흐름, 첫 양봉 저가 위 지지) → 당일 양봉이 첫 양봉 종가 돌파 |
| 돌파 대기 (A_near) | 모양은 완성됐지만 당일 양봉이 첫 양봉 종가 미달 |
| 3음봉 진행형 (B) | 장대양봉 → 음봉 3개, 당일이 세 번째 음봉 (다음 양봉 시 완성) |

## 다른 컴퓨터에서 스크리닝 돌리기

```bash
git clone https://github.com/vencent10004-droid/rising3-radar.git
cd rising3-radar
pip install -r tools/requirements.txt
python tools/daily_update.py
```

- Python 3.10+ 필요. 실행에 약 3~5분 (KRX 전종목 25영업일 시세 수집)
- 마지막 git push는 이 저장소에 push 권한이 있는 GitHub 계정으로 로그인돼 있어야 합니다
- 매일 자동 실행하려면 Windows 작업 스케줄러(또는 cron)에 평일 16:40 등록

## 구조

```
index.html            앱 화면 (정적, 수정 시 즉시 배포됨)
manifest.webmanifest  PWA 설정
sw.js                 서비스워커 (오프라인 캐시)
data/index.json       날짜 목록
data/rising3_*.json   일자별 스크리닝 결과
tools/daily_update.py 스크리닝 + 배포 올인원 스크립트
```

> 과거 시세 기반 패턴 검색 결과이며 투자 권유가 아닙니다.
