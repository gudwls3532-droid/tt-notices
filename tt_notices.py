#!/usr/bin/env python3
"""탁구대회 공지 모아보기 (틀)

사용법
  pip install requests beautifulsoup4
  python tt_notices.py --demo   # 샘플 데이터로 index.html 만들기 (인터넷 불필요)
  python tt_notices.py          # 실제 사이트 수집 후 index.html 만들기

수집 결과: notices.json / 화면: index.html (브라우저로 열기)
"""
import argparse, json, re, sys
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

# ── 1. 수집할 사이트 ───────────────────────────────────────────
# url: 대회 공지 '목록 게시판' 주소로 바꿔 넣으세요 (아래는 임시 메인 주소).
# parser: 사이트마다 전용 함수를 만들면 PARSERS에 등록 (없으면 generic 사용).
SOURCES = [
    {"name": "오케이핑퐁", "url": "https://www.okpingpong.co.kr", "parser": "generic"},
    {"name": "대한탁구협회", "url": "https://www.ktta.or.kr", "parser": "generic"},
    {"name": "아이핑클럽", "url": "", "parser": "generic"},      # TODO: 주소 입력
    {"name": "슈퍼스타탁구", "https://www.superstar.kr/open/Do.jsp?urlSeq=214": "", "parser": "generic"},    # TODO: 주소 입력
    {"name": "코리아탁구", "url": "", "parser": "generic"},      # TODO: 주소 입력
]

REGIONS = ["서울", "경기", "인천", "강원", "충북", "충남", "대전", "세종", "경북", "대구",
           "경남", "부산", "울산", "전북", "전남", "광주", "제주",
           "울진", "경산", "횡성", "원주", "천안", "광주"]
KEYWORD = re.compile(r"대회|오픈|배\b|리그|선수권")
HEADERS = {"User-Agent": "Mozilla/5.0 (tt-notices personal project)"}


# ── 2. 파서 ───────────────────────────────────────────────────
def find_date(text):
    """제목에서 대회 날짜를 찾아 'YYYY-MM-DD'로. 못 찾으면 ''."""
    m = re.search(r"(20\d{2})[.\-/ ]+(\d{1,2})[.\-/ ]+(\d{1,2})", text)
    if m:
        return f"{int(m[1]):04d}-{int(m[2]):02d}-{int(m[3]):02d}"
    m = re.search(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일", text)
    if m:
        y = date.today().year
        return f"{y:04d}-{int(m[1]):02d}-{int(m[2]):02d}"
    return ""


def find_region(text):
    return next((r for r in REGIONS if r in text), "")


def parse_generic(html, base_url, source_name):
    """링크 글자에 '대회/오픈/배' 등이 들어간 항목을 공지로 간주하는 임시 파서.
    사이트별로 정확하게 하려면 아래 예시처럼 전용 파서를 따로 만드세요."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    out, seen = [], set()
    for a in soup.find_all("a", href=True):
        title = " ".join(a.get_text().split())
        url = urljoin(base_url, a["href"])
        if len(title) < 6 or not KEYWORD.search(title) or url in seen:
            continue
        seen.add(url)
        out.append({"title": title, "date": find_date(title),
                    "region": find_region(title), "source": source_name, "url": url})
    return out


# 전용 파서 예시 (사이트 구조를 확인한 뒤 작성):
# def parse_okpingpong(html, base_url, source_name):
#     soup = BeautifulSoup(html, "html.parser")
#     for row in soup.select("table.board tr"):
#         ...
PARSERS = {"generic": parse_generic}


# ── 3. 수집 ───────────────────────────────────────────────────
def collect():
    import requests
    items = []
    for src in SOURCES:
        if not src["url"]:
            print(f"- {src['name']}: 주소 미입력, 건너뜀")
            continue
        try:
            r = requests.get(src["url"], headers=HEADERS, timeout=15)
            r.raise_for_status()
            r.encoding = r.apparent_encoding or "utf-8"
            found = PARSERS[src["parser"]](r.text, src["url"], src["name"])
            print(f"- {src['name']}: {len(found)}건")
            items += found
        except Exception as e:  # 한 사이트가 실패해도 나머지는 계속
            print(f"- {src['name']}: 실패 ({e})", file=sys.stderr)
    return items


def demo_items():
    return [dict(i, title="[샘플] " + i["title"]) for i in _DEMO]


_DEMO = [
        {"title": "제14회 울진금강송배 전국 탁구대회", "date": "2026-11-21", "region": "울진", "source": "샘플", "url": "https://example.com/1"},
        {"title": "2026 경산 삼성현배 전국 생활체육 탁구대회", "date": "2026-11-28", "region": "경산", "source": "샘플", "url": "https://example.com/2"},
        {"title": "서울시탁구협회장기 오픈대회", "date": "2026-12-05", "region": "서울", "source": "샘플", "url": "https://example.com/3"},
        {"title": "제주 한라배 전국 오픈 탁구대회", "date": "2026-12-12", "region": "제주", "source": "샘플", "url": "https://example.com/4"},
        {"title": "지난 달 열린 부산 오픈 탁구대회", "date": "2026-10-10", "region": "부산", "source": "샘플", "url": "https://example.com/5"},
        {"title": "날짜 미정 디비전 리그 개최 공지", "date": "", "region": "", "source": "샘플", "url": "https://example.com/6"},
    ]


def dedupe(items):
    seen, out = set(), []
    for it in items:
        key = (it["title"], it["date"])
        if key not in seen:
            seen.add(key)
            out.append(it)
    return out


# ── 4. 화면(HTML) 만들기 ──────────────────────────────────────
PAGE = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>탁구대회 모아보기</title>
<style>
:root{--bg:#f6f7f9;--ink:#16202c;--sub:#5c6b7a;--line:#d9dfe6;--card:#fff;--blue:#17406e;--ball:#e8761a}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#10161d;--ink:#e8edf2;--sub:#98a6b4;--line:#27323d;--card:#18212a;--blue:#7fb0e6;--ball:#f0903f}}
:root[data-theme="dark"]{--bg:#10161d;--ink:#e8edf2;--sub:#98a6b4;--line:#27323d;--card:#18212a;--blue:#7fb0e6;--ball:#f0903f}
html{scroll-padding-top:env(safe-area-inset-top,0px)}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 "Apple SD Gothic Neo","Malgun Gothic","Noto Sans KR",sans-serif}
main{max-width:860px;margin:0 auto;padding:calc(24px + env(safe-area-inset-top,0px)) 16px calc(48px + env(safe-area-inset-bottom,0px))}
[hidden]{display:none!important}
.tabs{display:flex;gap:0;margin-bottom:12px}
.tabs button{font:inherit;padding:7px 18px;border:1px solid var(--line);background:var(--card);color:var(--sub);cursor:pointer}
.tabs button:first-child{border-radius:6px 0 0 6px}.tabs button:last-child{border-radius:0 6px 6px 0;border-left:0}
.tabs button[aria-pressed="true"]{background:var(--blue);border-color:var(--blue);color:var(--bg)}
.calhead{display:flex;align-items:center;gap:10px;margin-bottom:8px}
.calhead strong{flex:1;text-align:center;font-size:1.1rem}
.calhead button{font:inherit;padding:4px 12px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--ink);cursor:pointer}
.grid{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:1px;background:var(--line);border:1px solid var(--line);margin-bottom:12px}
.grid>*{background:var(--card);min-width:0}
.dow{text-align:center;font-size:.8rem;color:var(--sub);padding:4px 0}
.blank{min-height:78px;background:var(--bg)!important}
.day{min-height:78px;padding:4px;border:0;text-align:left;font:inherit;color:var(--ink);cursor:pointer;display:block;overflow:hidden}
.day .n{display:block;font-size:.85rem;font-variant-numeric:tabular-nums}
.day.today .n{color:var(--ball);font-weight:700}
.day.sel{outline:2px solid var(--ball);outline-offset:-2px}
.day:focus-visible,.calhead button:focus-visible,.tabs button:focus-visible{outline:2px solid var(--ball);outline-offset:2px}
.chip{display:block;margin-top:2px;padding:1px 4px;border-radius:3px;background:var(--blue);color:var(--bg);font-size:.72rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.chip.soon{background:var(--ball)}
.more{font-size:.72rem;color:var(--sub)}
@media (max-width:480px){.day,.blank{min-height:58px}.chip{display:inline-block;width:7px;height:7px;padding:0;margin:3px 2px 0 0;border-radius:50%;font-size:0}}
.links{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px}
.links a{font-weight:500;font-size:.9rem;padding:6px 10px;border:1px solid var(--line);border-radius:6px;background:var(--card)}
details{margin-top:20px;color:var(--sub)}
summary{cursor:pointer}
.add{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px}
.add input,.add button{font:inherit;padding:8px 10px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--ink)}
.add .w{grid-column:1/-1}
.add button{cursor:pointer;background:var(--blue);color:var(--bg);border-color:var(--blue)}
li .del{font:inherit;font-size:.85rem;border:0;background:none;color:var(--sub);cursor:pointer;padding:0;margin-left:8px;text-decoration:underline}
h1{font-size:1.5rem;margin:0 0 4px}
.meta{color:var(--sub);font-size:.9rem;margin-bottom:16px}
.bar{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px}
.bar input,.bar select{font:inherit;padding:8px 10px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--ink)}
.bar input{flex:1;min-width:160px}
.bar label{display:flex;align-items:center;gap:6px;color:var(--sub)}
ul{list-style:none;margin:0;padding:0}
li{display:grid;grid-template-columns:96px 1fr;gap:4px 14px;padding:14px 4px;border-top:1px solid var(--line)}
li:last-child{border-bottom:1px solid var(--line)}
.d{font-weight:700;color:var(--blue);font-variant-numeric:tabular-nums}
.d small{display:block;font-weight:400;color:var(--sub)}
.soon .d{color:var(--ball)}
a{color:var(--ink);text-decoration:none;font-weight:600}
a:hover{text-decoration:underline}
a:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid var(--ball);outline-offset:2px}
.t{color:var(--sub);font-size:.88rem}
.empty{padding:32px 4px;color:var(--sub)}
@media (max-width:480px){li{grid-template-columns:1fr}}
</style></head><body><main>
<h1>탁구대회 모아보기</h1>
<div class="meta" id="meta"></div>
<div class="links" id="links"></div>
<div class="tabs" role="group" aria-label="보기 방식"><button id="tab_cal" type="button">달력</button><button id="tab_list" type="button">목록</button></div>
<div class="bar">
  <input id="q" type="search" placeholder="대회 이름 검색" aria-label="대회 이름 검색">
  <select id="region" aria-label="지역"><option value="">전체 지역</option></select>
  <select id="source" aria-label="출처"><option value="">전체 사이트</option></select>
  <label id="pastwrap"><input id="past" type="checkbox"> 지난 대회 보기</label>
</div>
<div id="cal"></div>
<ul id="list"></ul>
<details><summary>직접 대회 추가하기 (이 브라우저에만 저장)</summary>
<div class="add">
  <input id="n_title" class="w" placeholder="대회 이름" aria-label="대회 이름">
  <input id="n_date" type="date" aria-label="대회 날짜">
  <input id="n_region" placeholder="지역 (예: 서울)" aria-label="지역">
  <input id="n_url" class="w" type="url" placeholder="원본 공지 링크 (https://...)" aria-label="원본 공지 링크">
  <button id="n_add" class="w" type="button">추가</button>
</div></details>
<script>
const BASE = __DATA__;
const LINKS = __LINKS__;
const UPDATED = "__UPDATED__";
const KEY = "tt_mine";
const $ = id => document.getElementById(id);
const today = new Date().toISOString().slice(0,10);
const DOW = "일월화수목금토";
let MINE = [];
try { MINE = JSON.parse(localStorage.getItem(KEY) || "[]"); } catch (e) { MINE = []; }
function save(){ try { localStorage.setItem(KEY, JSON.stringify(MINE)); } catch (e) {} }
const all = () => BASE.concat(MINE);
function fill(sel, key, label){
  const cur = sel.value;
  sel.innerHTML = '<option value="">' + label + '</option>';
  [...new Set(all().map(x=>x[key]).filter(Boolean))].sort().forEach(v=>{
    const o=document.createElement("option");o.value=o.textContent=v;sel.appendChild(o);});
  sel.value = cur;
}
LINKS.forEach(l=>{const a=document.createElement("a");a.href=l.url;a.target="_blank";a.rel="noopener";a.textContent=l.name;$("links").appendChild(a);});
function fmt(d){
  if(!d) return ["날짜 미정",""];
  const dt=new Date(d+"T00:00:00");
  return [`${dt.getMonth()+1}/${dt.getDate()}`, DOW[dt.getDay()]+"요일"];
}
const pad = n => String(n).padStart(2,"0");
const monthStart = () => new Date(today.slice(0,7)+"-01T00:00:00");
let view = "cal", cur = monthStart(), sel = "";
const daysTo = d => d ? (new Date(d) - new Date(today)) / 864e5 : 99;
function rowEl(x){
  const [d,w]=fmt(x.date);
  const days=daysTo(x.date);
  const li=document.createElement("li");
  if(days>=0&&days<=7) li.className="soon";
  const a=document.createElement("a");a.href=x.url||"#";a.target="_blank";a.rel="noopener";a.textContent=x.title;
  const dd=document.createElement("div");dd.className="d";dd.innerHTML=d+"<small>"+w+"</small>";
  const body=document.createElement("div");body.appendChild(a);
  const t=document.createElement("div");t.className="t";
  t.textContent=[x.region||"지역 미확인",x.source].join(" · ");
  if(x.mine){const b=document.createElement("button");b.type="button";b.className="del";b.textContent="삭제";
    b.onclick=()=>{MINE=MINE.filter(m=>m.id!==x.id);save();render();};t.appendChild(b);}
  body.appendChild(t);
  li.append(dd,body);
  return li;
}
function renderCal(rows){
  const y=cur.getFullYear(), m=cur.getMonth();
  const first=new Date(y,m,1).getDay(), last=new Date(y,m+1,0).getDate();
  const ym=`${y}-${pad(m+1)}`;
  const by={};
  rows.forEach(x=>{ if(x.date&&x.date.startsWith(ym)) (by[x.date]=by[x.date]||[]).push(x); });
  const box=$("cal"); box.innerHTML="";
  const head=document.createElement("div"); head.className="calhead";
  const mk=(txt,fn,label)=>{const b=document.createElement("button");b.type="button";b.textContent=txt;b.setAttribute("aria-label",label||txt);b.onclick=fn;return b;};
  const title=document.createElement("strong"); title.textContent=`${y}년 ${m+1}월`;
  head.append(
    mk("‹",()=>{cur=new Date(y,m-1,1);sel="";render();},"이전 달"),
    title,
    mk("›",()=>{cur=new Date(y,m+1,1);sel="";render();},"다음 달"),
    mk("오늘",()=>{cur=monthStart();sel=today;render();}));
  box.appendChild(head);
  const grid=document.createElement("div"); grid.className="grid";
  [...DOW].forEach(c=>{const h=document.createElement("div");h.className="dow";h.textContent=c;grid.appendChild(h);});
  for(let i=0;i<first;i++){const e=document.createElement("div");e.className="blank";grid.appendChild(e);}
  for(let d=1;d<=last;d++){
    const key=`${ym}-${pad(d)}`, ev=by[key]||[];
    const c=document.createElement("button");c.type="button";
    c.className="day"+(key===today?" today":"")+(key===sel?" sel":"");
    c.setAttribute("aria-label",`${m+1}월 ${d}일, 대회 ${ev.length}개`);
    const n=document.createElement("span");n.className="n";n.textContent=d;c.appendChild(n);
    ev.slice(0,2).forEach(x=>{
      const s=document.createElement("span");const dt=daysTo(x.date);
      s.className="chip"+(dt>=0&&dt<=7?" soon":"");s.textContent=x.title;c.appendChild(s);});
    if(ev.length>2){const s=document.createElement("span");s.className="more";s.textContent="+"+(ev.length-2);c.appendChild(s);}
    c.onclick=()=>{sel=(sel===key?"":key);render();};
    grid.appendChild(c);
  }
  box.appendChild(grid);
}
function render(){
  fill($("region"),"region","전체 지역"); fill($("source"),"source","전체 사이트");
  const q=$("q").value.trim(), r=$("region").value, s=$("source").value, past=$("past").checked;
  const cal=view==="cal";
  $("cal").hidden=!cal; $("pastwrap").hidden=cal;
  $("tab_cal").setAttribute("aria-pressed",cal); $("tab_list").setAttribute("aria-pressed",!cal);
  const rows=all().filter(x=>(!q||x.title.includes(q))&&(!r||x.region===r)&&(!s||x.source===s)
      &&(cal||past||!x.date||x.date>=today))
    .sort((a,b)=>(a.date||"9999").localeCompare(b.date||"9999"));
  let show=rows, note="";
  if(cal){
    renderCal(rows);
    const ym=`${cur.getFullYear()}-${pad(cur.getMonth()+1)}`;
    show = sel ? rows.filter(x=>x.date===sel) : rows.filter(x=>x.date&&x.date.startsWith(ym));
    const und=rows.filter(x=>!x.date).length;
    if(und) note=` · 날짜 미정 ${und}개는 목록에서 확인`;
  }
  $("list").innerHTML = show.length ? "" : `<li class="empty">${cal&&sel?"이 날은 대회가 없습니다.":cal?"이 달에는 대회가 없습니다.":"조건에 맞는 대회가 없습니다."}</li>`;
  show.forEach(x=>$("list").appendChild(rowEl(x)));
  $("meta").textContent=`${show.length}개 표시 · 수집 ${UPDATED}${note}`;
}
$("tab_cal").onclick=()=>{view="cal";render();};
$("tab_list").onclick=()=>{view="list";render();};
$("n_add").onclick=()=>{
  const title=$("n_title").value.trim(); if(!title){$("n_title").focus();return;}
  MINE.push({id:Date.now(),mine:true,title,date:$("n_date").value,region:$("n_region").value.trim(),
    source:"직접 추가",url:$("n_url").value.trim()});
  save(); ["n_title","n_date","n_region","n_url"].forEach(i=>$(i).value=""); render();
};
["q","region","source","past"].forEach(id=>$(id).addEventListener("input",render));
render();
</script></main></body></html>
"""


def build_page(items, out_path):
    data = json.dumps(items, ensure_ascii=False).replace("</", "<\\/")
    links = json.dumps([{"name": x["name"], "url": x["url"]} for x in SOURCES if x["url"]], ensure_ascii=False)
    html = PAGE.replace("__LINKS__", links).replace("__DATA__", data).replace("__UPDATED__", date.today().isoformat())
    Path(out_path).write_text(html, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="샘플 데이터로 실행")
    args = ap.parse_args()
    here = Path(__file__).parent
    items = dedupe(demo_items() if args.demo else collect())
    (here / "notices.json").write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    build_page(items, here / "index.html")
    print(f"완료: {len(items)}건 → {here / 'index.html'}")


if __name__ == "__main__":
    main()
