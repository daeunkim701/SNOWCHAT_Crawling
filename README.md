# 눈송 공지비서 · 공지 크롤러

> 2026 SNOWCHAT AI 서비스 경진대회 출품작 **「눈송 공지비서; 시그마」**의 데이터 수집 모듈

숙명여자대학교 대표 홈페이지와 학과 홈페이지에 흩어진 **공개 공지 게시판**을 수집해 하나의 JSON으로 통합합니다.
수집한 데이터는 이후 단계(구조화 추출 → 지식그래프 구축 → 관심사 알림·SNOWCHAT 챗봇)의 입력으로 사용됩니다.

<br>

## 주요 기능

| 기능 | 설명 |
|---|---|
| 다중 게시판 수집 | 같은 CMS를 쓰는 대표 홈페이지·학과 게시판을 하나의 범용 크롤러로 수집 |
| 증분 수집 | 마지막으로 수집한 글 번호 이후의 새 글만 가져옴 (상단 고정글은 판단에서 제외) |
| 중복 제거 | `source:id` 조합을 고유 키로 사용해 게시판이 달라도 ID 충돌 없음 |
| 데이터 정규화 | 날짜 형식 통일(`2026-10-12` → `2026.10.12`), 상세 URL에서 불필요한 파라미터 제거 |
| 장애 격리 | 한 게시판 수집이 실패해도 나머지 게시판은 계속 수집 |

<br>

## 1차 수집 테스트 대상

| source | 게시판 | URL |
|---|---|---|
| `sm_main` | 숙명여대 주요 공지 | `https://www.sookmyung.ac.kr/kr/news/important-notice.do` |
| `dept_math` | 수학과 공지사항 | `https://math.sookmyung.ac.kr/math/notice/notice.do` |

대표 홈페이지와 학과 홈페이지는 같은 CMS를 사용해 아래 구조가 동일합니다.

| 항목 | 형식 |
|---|---|
| 목록 | `?mode=list&articleLimit=10&article.offset=0, 10, 20 ...` |
| 상세 | `?mode=view&articleNo={글 번호}` |
| 고정글 | 번호 칸에 `공지` 표시 |
| 렌더링 | 서버 렌더링 HTML (JS 실행 불필요) |

<br>

## 프로젝트 구조

```
crawler/
├── common.py      # 공통 스키마, 저장, 중복 제거, 소스별 증분 상태 관리
├── sm_board.py    # 공통 CMS 게시판 범용 크롤러 + 게시판 목록(BOARDS)
├── run.py         # 실행 진입점 (CLI)
└── data/          # 실행 시 자동 생성
    ├── notices.json   # 전체 소스 통합 결과
    └── state.json     # 소스별 마지막 수집 글 번호
```

<br>

## 시작하기

### 요구 사항
- Python 3.10 이상

### 설치
```bash
pip install -r requirements.txt
```

### 실행
```bash
python run.py                              # 등록된 전체 게시판, 최근 3페이지
python run.py --sources sm_main dept_math  # 특정 게시판만
python run.py --pages 10                   # 페이지 수 지정 (1페이지 = 10건)
python run.py --incremental                # 마지막 수집 이후 새 글만
```

| 옵션 | 기본값 | 설명 |
|---|---|---|
| `--sources` | 전체 | 수집할 source 키 목록 |
| `--pages` | `3` | 수집할 목록 페이지 수 |
| `--incremental` | 꺼짐 | 새 글만 수집 (최대 50페이지까지 내려가며 이미 본 글이 나오면 중단) |

### 실행 결과 예시
```
[sm_main] 수집 30건 / 신규 30건
[dept_math] 수집 30건 / 신규 30건

총 60건 → data/notices.json
```

<br>

## 데이터 형식

`data/notices.json`에는 아래 형식의 객체 배열이 날짜 내림차순으로 저장됩니다.

```json
{
  "source": "sm_main",
  "board": "숙명여대 주요 공지",
  "id": "95613",
  "title": "[학부] 2027학년도 전과 모집 요강 및 여석 공고",
  "category": "학사",
  "date": "2026.10.20",
  "pinned": false,
  "url": "https://www.sookmyung.ac.kr/kr/news/important-notice.do?mode=view&articleNo=95613",
  "is_mock": false
}
```

| 필드 | 설명 |
|---|---|
| `source` | 데이터 출처 키 |
| `board` | 게시판 이름 (챗봇 답변·알림 표시용) |
| `id` | 게시판 내 고유 글 번호 |
| `title` | 공지 제목 |
| `category` | 게시판 자체 분류 탭 (대표 홈페이지: 공지·학사·등록·장학·모집·행정 / 학과: 없음) |
| `date` | 게시일 (`YYYY.MM.DD`) |
| `pinned` | 상단 고정글 여부 |
| `url` | 상세 페이지 링크 |
| `is_mock` | 가상 샘플 데이터 여부 |

<br>

## 게시판 추가하기

같은 CMS를 쓰는 게시판은 `sm_board.py`의 `BOARDS`에 한 줄만 추가하면 됩니다.

```python
BOARDS = {
    ...
    "dept_xxx": Board(
        source="dept_xxx",
        name="OO학과 공지사항",
        list_url="https://<학과 도메인>/<경로>/notice/notice.do",
    ),
}
```

추가 전 확인할 것
1. 공지 상세 링크가 `?mode=view&articleNo=` 형식인지
2. `robots.txt`에서 해당 경로가 허용되는지
3. 로그인 없이 목록이 보이는지

형식이 다른 사이트는 `crawl(pages, incremental)` 함수를 가진 별도 모듈을 만들고 `run.py`의 `CRAWLERS`에 등록합니다.

<br>

## 수집 정책

본 크롤러는 공개된 정보만 학교 서버에 부담을 주지 않는 범위에서 수집합니다.

| 원칙 | 적용 |
|---|---|
| robots.txt 준수 | 수집 전 사이트별 robots.txt 확인. `Disallow`된 경로와 서버 오류(5xx)로 확인이 불가한 사이트는 제외 |
| 공개 페이지만 | 로그인이 필요한 페이지는 수집하지 않음 |
| 서버 부하 최소화 | 요청 간격 1초 이상 (`DELAY_SEC`), 증분 수집으로 요청 수 최소화 |
| 최소 수집 | 현재는 제목·게시일·분류·링크만 수집 (본문·첨부 미수집) |
| 개인정보 보호 | 공지 속 개인정보를 수집·가공하지 않음. 본문 수집 시 연락처·이메일·학번 마스킹 예정 |

### 수집하지 않는 대상
| 대상 | 사유 | 대안 |
|---|---|---|
| SnoWe | 로그인 필요 | 가상 샘플 데이터로 기능 검증, 대학 도입 시 공식 연동 |
| SNOWISE | 자동 접근 제한 | 동일 |
| 학생회 SNS | 플랫폼 약관상 무단 수집 불가 | 학생회 협조 시 공식 API 연동 |

<br>

## 한계 및 향후 계획

- [ ] 학과 게시판 확대 (현재 수학과만 구조 확인 완료)
- [ ] 교내 기관·부서 사이트 수집 모듈 추가 (CMS가 다른 사이트는 별도 파서 필요)
- [ ] 상세 페이지 본문 수집 + 개인정보 마스킹
- [ ] 첨부파일 텍스트 추출 (PDF → HWP/HWPX → 이미지 OCR 순으로 단계적 확대)
- [ ] 본문 해시 기반 수정 감지
- [ ] 공개 조회수 일별 스냅샷
- [ ] JSON 저장 → MySQL 적재로 전환

<br>

## 참고

- 본 저장소는 경진대회 출품을 위한 프로토타입입니다.
- 각 공지의 저작권은 게시 기관에 있으며, 본 서비스는 원문 링크로 안내합니다.
