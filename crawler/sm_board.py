"""
숙명여대 공통 CMS 게시판 범용 크롤러

메인 홈페이지와 학과 홈페이지가 같은 CMS를 사용한다.
  - 목록:   <게시판URL>?mode=list&articleLimit=10&article.offset=0,10,20...
  - 상세:   <게시판URL>?mode=view&articleNo=<ID>
  - 고정글: 번호 칸에 "공지"
  - 날짜:   메인은 2026.10.20 / 학과는 2026-10-12 → 2026.10.20 형식으로 통일

새 게시판 추가는 BOARDS에 한 줄만 넣으면 된다.
"""
import re
import time
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

from common import HEADERS, get_last_seen, set_last_seen

PAGE_SIZE = 10
DELAY_SEC = 1.0
MAX_PAGES_INCREMENTAL = 50  # 증분 모드 안전장치
DATE_RE = re.compile(r"\d{4}[.\-]\d{2}[.\-]\d{2}")


@dataclass
class Board:
    source: str                      # 데이터 출처 키 (예: "sm_main", "dept_math")
    name: str                        # 사람이 읽는 이름 (챗봇 답변용)
    list_url: str                    # 게시판 주소 (쿼리스트링 없이)
    categories: list[str] = field(default_factory=list)  # 제목 칸 앞에 붙는 분류 (없으면 빈 리스트)


# ======================= 게시판 등록 =======================
# 학과 추가 시: 학과 홈페이지 > 공지사항 메뉴 주소를 넣으면 된다.
BOARDS = {
    "sm_main": Board(
        source="sm_main",
        name="숙명여대 주요 공지",
        list_url="https://www.sookmyung.ac.kr/kr/news/important-notice.do",
        categories=["공지", "학사", "등록", "장학", "모집", "행정"],
    ),
    "dept_math": Board(
        source="dept_math",
        name="수학과 공지사항",
        list_url="https://math.sookmyung.ac.kr/math/notice/notice.do",
    ),
}
# ==========================================================


def fetch_page(board: Board, page: int) -> str:
    params = {"mode": "list", "articleLimit": PAGE_SIZE, "article.offset": page * PAGE_SIZE}
    res = requests.get(board.list_url, params=params, headers=HEADERS, timeout=10)
    res.raise_for_status()
    return res.text


def parse(board: Board, html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    items, seen = [], set()

    for a in soup.select('a[href*="mode=view"][href*="articleNo="]'):
        href = urljoin(board.list_url, a["href"])
        article_no = parse_qs(urlparse(href).query).get("articleNo", [None])[0]
        if not article_no or article_no in seen:
            continue
        seen.add(article_no)

        row = a.find_parent("tr")
        cells = row.find_all("td") if row else []
        row_text = row.get_text(" ", strip=True) if row else ""
        first_cell = cells[0].get_text(strip=True) if cells else ""
        title_cell = cells[1].get_text(" ", strip=True) if len(cells) > 1 else ""

        date_match = DATE_RE.search(row_text)
        category = next((c for c in board.categories if title_cell.startswith(c)), None)

        items.append({
            "source": board.source,
            "board": board.name,
            "id": article_no,
            "title": a.get_text(" ", strip=True),
            "category": category,
            "date": date_match.group().replace("-", ".") if date_match else None,
            "pinned": first_cell == "공지",
            "url": f"{board.list_url}?mode=view&articleNo={article_no}",
        })
    return items


def crawl_board(board: Board, pages: int = 3, incremental: bool = False) -> list[dict]:
    last_seen = int(get_last_seen(board.source) or 0)
    collected = []

    for page in range(MAX_PAGES_INCREMENTAL if incremental else pages):
        items = parse(board, fetch_page(board, page))
        if not items:
            break
        collected.extend(items)

        # 증분 모드: 고정글은 제외하고, 이미 본 글까지 내려오면 중단
        # (학과 게시판은 오래된 글도 고정돼 있어서 고정글을 기준에서 빼야 함)
        normal_ids = [int(i["id"]) for i in items if not i["pinned"]]
        if incremental and normal_ids and min(normal_ids) <= last_seen:
            break
        time.sleep(DELAY_SEC)

    if collected:
        set_last_seen(board.source, max([last_seen] + [int(i["id"]) for i in collected]))
    return collected