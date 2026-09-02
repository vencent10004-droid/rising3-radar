# -*- coding: utf-8 -*-
"""상승 삼법형 일일 스크리닝 + 배포 (올인원, 어느 컴퓨터에서든 실행 가능)

사용법:
  1) git clone https://github.com/vencent10004-droid/rising3-radar.git
  2) pip install -r tools/requirements.txt
  3) python tools/daily_update.py          # 스크리닝 + data/ 갱신 + git push

- 코스피+코스닥 전종목 최근 25영업일 시세를 KRX에서 수집 (약 3~5분)
- 패턴 검사 후 data/rising3_{기준일}.json 저장, data/index.json 갱신
- git commit & push (push 권한이 있는 계정으로 git 로그인 필요)
"""
import sys, io, os, time, json, subprocess
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from datetime import datetime, timedelta
import pandas as pd
from pykrx import stock

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(REPO, "data")
os.makedirs(DATA, exist_ok=True)

# ---- 1) 최근 영업일 ----
today = datetime.now().strftime("%Y%m%d")
start = (datetime.now() - timedelta(days=60)).strftime("%Y%m%d")
days = [d.strftime("%Y%m%d") for d in stock.get_previous_business_days(fromdate=start, todate=today)]
need_days = days[-25:]
latest = need_days[-1]
print("기준일(최근 영업일):", latest)

# ---- 2) 전종목 시세 수집 ----
mkt_of = {}
for mkt in ("KOSPI", "KOSDAQ"):
    df = stock.get_market_cap_by_ticker(latest, market=mkt)
    df = df.sort_values("시가총액", ascending=False)
    for rank, t in enumerate(df.index, 1):
        mkt_of[t] = (mkt, int(df.loc[t, "시가총액"]), rank)
print("전종목:", len(mkt_of))

frames = {}
for d in need_days:
    rows = []
    for mkt in ("KOSPI", "KOSDAQ"):
        rows.append(stock.get_market_ohlcv_by_ticker(d, market=mkt))
        time.sleep(0.3)
    frames[d] = pd.concat(rows)
    print("fetched", d, flush=True)

# ---- 3) 패턴 검사 ----
def series_for(t):
    recs = []
    for d in need_days:
        df = frames[d]
        if t in df.index:
            r = df.loc[t]
            if r["시가"] > 0:
                recs.append((d, float(r["시가"]), float(r["고가"]), float(r["저가"]), float(r["종가"]), float(r["거래량"])))
    return recs

def body(r): return abs(r[4] - r[1])
def is_bull(r): return r[4] > r[1]
def is_bear(r): return r[4] < r[1]

resA, resA_near, resB = [], [], []
checked = 0
for t in mkt_of:
    recs = series_for(t)
    if len(recs) < 10 or recs[-1][0] != latest:
        continue
    checked += 1
    closes = [r[4] for r in recs]
    ma20 = sum(closes[-20:]) / len(closes[-20:])

    row_common = dict(ticker=t, name=stock.get_market_ticker_name(t), mkt=mkt_of[t][0],
                      mcap=round(mkt_of[t][1] / 1e8), rank=mkt_of[t][2],
                      avgVol5=int(sum(r[5] for r in recs[-5:]) / 5),
                      candles=[[r[0], r[1], r[2], r[3], r[4]] for r in recs[-6:]])

    d0, d1, d2, d3, d4 = recs[-5:]
    b0 = body(d0)
    if (is_bull(d0) and b0/d0[1] >= 0.015 and
            all(is_bear(x) for x in (d1, d2, d3)) and
            all(body(x) < b0 for x in (d1, d2, d3)) and
            d3[4] < d1[4] and
            min(d1[3], d2[3], d3[3]) >= d0[3] and
            is_bull(d4) and body(d4)/d4[1] >= 0.01):
        row = dict(row_common, close=d4[4], chg=round((d4[4]/d3[4]-1)*100, 2),
                   d0Close=d0[4], aboveMa20=d4[4] > ma20)
        (resA if d4[4] > d0[4] else resA_near).append(row)

    e0, e1, e2, e3 = recs[-4:]
    b0 = body(e0)
    if (is_bull(e0) and b0/e0[1] >= 0.015 and
            all(is_bear(x) for x in (e1, e2, e3)) and
            all(body(x) < b0 for x in (e1, e2, e3)) and
            e3[4] < e1[4] and
            min(e1[4], e2[4], e3[4]) > e0[1]):
        resB.append(dict(row_common, close=e3[4], chg=round((e3[4]/e2[4]-1)*100, 2),
                         d0Body=round(b0/e0[1]*100, 2), aboveMa20=e3[4] > ma20))

def sort_mcap(res): return sorted(res, key=lambda x: -x["mcap"])
doc = dict(date=latest,
           updatedAt=datetime.now().astimezone().isoformat(timespec="seconds"),
           checked=checked, universe=len(mkt_of),
           A=sort_mcap(resA), A_near=sort_mcap(resA_near), B=sort_mcap(resB))

with open(os.path.join(DATA, f"rising3_{latest}.json"), "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False)

idx_path = os.path.join(DATA, "index.json")
dates = set()
if os.path.exists(idx_path):
    with open(idx_path, encoding="utf-8") as f:
        dates = set(json.load(f).get("dates", []))
dates.add(latest)
with open(idx_path, "w", encoding="utf-8") as f:
    json.dump({"dates": sorted(dates)}, f, ensure_ascii=False)

print(f"\n결과 — 완성형 {len(resA)} / 돌파대기 {len(resA_near)} / 3음봉 진행 {len(resB)}")

# ---- 4) git push ----
def git(*args):
    r = subprocess.run(["git", "-C", REPO, *args], capture_output=True, text=True)
    out = (r.stdout or r.stderr).strip()
    if out: print("git", args[0], "->", out[:200])
    return r

git("pull", "--rebase")
git("add", "data")
st = subprocess.run(["git", "-C", REPO, "status", "--porcelain"], capture_output=True, text=True)
if not st.stdout.strip():
    print("변경 없음 — 커밋/푸시 생략")
else:
    git("commit", "-m", f"data: {latest} screening results")
    if git("push").returncode != 0:
        print("push 실패 — git 로그인/권한 확인 필요")
        sys.exit(1)
    print("배포 완료: https://vencent10004-droid.github.io/rising3-radar/ (반영 1~2분)")
