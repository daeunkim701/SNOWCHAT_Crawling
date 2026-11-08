"""
실행 진입점

사용법:
  pip install requests beautifulsoup4
  python run.py                              # 등록된 전체 소스, 최근 3페이지
  python run.py --sources sm_main dept_math  # 특정 소스만
  python run.py --incremental                # 새 글만
  python run.py --pages 10

결과: data/notices.json (전 소스 통합), data/state.json (소스별 증분 상태)
"""
import argparse
from functools import partial

import common
import sm_board

# 공통 CMS 게시판(메인·학과)
# 다른 형식의 사이트를 추가할 때는 crawl(pages, incremental) 함수를 가진 모듈을 만들어 여기에 등록
CRAWLERS = {
    key: partial(sm_board.crawl_board, board) for key, board in sm_board.BOARDS.items()
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", nargs="+", default=list(CRAWLERS), choices=list(CRAWLERS))
    ap.add_argument("--pages", type=int, default=3)
    ap.add_argument("--incremental", action="store_true")
    args = ap.parse_args()

    store = common.load_store()

    for name in args.sources:
        try:
            items = CRAWLERS[name](pages=args.pages, incremental=args.incremental)
            new = common.merge(store, items)
            print(f"[{name}] 수집 {len(items)}건 / 신규 {new}건")
        except Exception as e:  # 한 소스가 실패해도 나머지는 계속
            print(f"[{name}] 실패: {e}")

    common.save_store(store)
    print(f"\n총 {len(store)}건 → {common.OUT_FILE}")
    for n in list(store.values())[:5]:
        print(f"  [{n.get('board', n['source'])}] {n['date']} {n['title']}\n    {n['url']}")


if __name__ == "__main__":
    main()