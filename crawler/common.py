"""
공통 모듈: 데이터 스키마, 저장, 중복 제거, 소스별 증분 상태 관리

모든 크롤러는 아래 형식의 dict 리스트를 반환해야 한다.
{
    "source":   "sm_main" | "dept_math" | ..., # 데이터 출처
    "board":    "수학과 공지사항",              # 게시판 이름 (챗봇 답변용)
    "id":       "95613",                       # 소스 내 고유 ID (문자열)
    "title":    "공지 제목",
    "category": "학사" | None,
    "date":     "2026.10.20" | None,
    "pinned":   False,                         # 상단 고정글 여부
    "url":      "https://...",                 # 사용자에게 돌려줄 링크
    "is_mock":  False,                         # 목데이터 여부 (챗봇 답변에 표시용)
}
"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
OUT_FILE = DATA_DIR / "notices.json"
STATE_FILE = DATA_DIR / "state.json"

HEADERS = {"User-Agent": "Mozilla/5.0 (SNOWCHAT contest MVP crawler)"}
REQUIRED_KEYS = {"source", "id", "title", "url"}


def _load(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path: Path, data) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def key_of(item: dict) -> str:
    """소스가 달라도 ID가 겹치지 않도록 'source:id'를 전역 키로 사용"""
    return f"{item['source']}:{item['id']}"


def load_store() -> dict[str, dict]:
    return {key_of(n): n for n in _load(OUT_FILE, [])}


def save_store(store: dict[str, dict]) -> None:
    notices = sorted(
        store.values(),
        key=lambda n: (n.get("date") or "", n["source"], n["id"]),
        reverse=True,
    )
    _save(OUT_FILE, notices)


def get_last_seen(source: str):
    return _load(STATE_FILE, {}).get(source)


def set_last_seen(source: str, value) -> None:
    state = _load(STATE_FILE, {})
    state[source] = value
    _save(STATE_FILE, state)


def normalize(item: dict) -> dict:
    missing = REQUIRED_KEYS - item.keys()
    if missing:
        raise ValueError(f"필수 필드 누락 {missing}: {item}")
    item["id"] = str(item["id"])
    item.setdefault("category", None)
    item.setdefault("date", None)
    item.setdefault("pinned", False)
    item.setdefault("is_mock", False)
    return item


def merge(store: dict[str, dict], items: list[dict]) -> int:
    """store에 items를 합치고 새로 추가된 개수를 반환"""
    new_count = 0
    for it in map(normalize, items):
        k = key_of(it)
        if k not in store:
            new_count += 1
        store[k] = it
    return new_count