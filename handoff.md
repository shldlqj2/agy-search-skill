# AGY 검색 MCP 재개 인계

최종 갱신: 2026-09-22. 이 문서는 중단 후 같은 저장소에서 안전하게 이어가기 위한 상태 기록이며, 다른 에이전트에 실행을 넘긴 상태가 아니다.

## 현재 상태

사용자 목표인 “AGY를 Google 검색엔진처럼 Codex에서 MCP 도구로 사용”하는 기본 전환 구현은 완료했다. 새 인터페이스는 `agy_search`와 `agy_fetch`이며, AGY만 검색·페이지 읽기를 수행한다. 서버는 AGY child process 하나를 직접 기다리며 Codex subagent, watcher, status polling, 내장 검색 fallback을 만들지 않는다.

- 저장소: `/home/ssafy/workspace/playground/agySearch`
- 브랜치: `main`
- 이 작업 시작 HEAD: `2c3cad4` (`Raise adaptive AGY timeout default`)
- 현재 작업은 아직 커밋·푸시 전이다. `git status --short --branch`를 먼저 확인한다.
- 이 문서, `plan.md`, `docs/agy-search-mcp-plan.ko.md`, MCP source/test/install 파일이 이번 작업의 변경 범위다.
- 마지막 live AGY search/fetch는 종료했고, 이 작업이 소유한 실행 중 AGY 또는 MCP process는 없다.
- 실제 사용자 Codex config 등록과 전역 Python package 설치는 하지 않았다. `install-mcp.* --dry-run`만 실행했다.

## 구현된 구성

- `pyproject.toml`: Python 3.10+, `mcp==2.2.0`, `agy-search-mcp` stdio entry point.
- `src/agy_search_mcp/backend.py`: AGY async supervisor, per-request artifacts, NDJSON parser, dangerous-tool audit, source ID index, artifact HTML text conversion, search/fetch provenance gate.
- `src/agy_search_mcp/server.py`: MCPServer와 `agy_search`, `agy_fetch` 도구. stderr logging만 허용하며 stdout은 protocol 전용이다.
- `tests/`: fake trace, concurrency/busy, cancellation cleanup, source fallback labeling, direct MCP client handshake 테스트.
- `install-mcp.sh`, `install-mcp.ps1`: package install + Codex local stdio MCP registration + `startup_timeout_sec = 30`, `tool_timeout_sec = 660` 설정. 기존 legacy skill은 자동 삭제하지 않는다.
- `README.md`, `README.ko.md`, `AGENTS.md`: MCP가 canonical이고 legacy skill은 호환성 surface임을 명시.

Timeout 정책은 `quick=180초`, `standard=300초`, `deep=600초`; 명시 `timeout_seconds`는 1–600초다. fetch의 기본은 300초다. 동시 실행은 1개이며 두 번째 호출은 숨은 queue/poll 대신 `busy` 오류를 받는다.

## 검증 결과

현재 local `.mcp-dev-deps`를 사용해 통과:

```bash
PYTHONPATH=src:.mcp-dev-deps python3 -m unittest discover -s tests -v
PYTHONPATH=src:.mcp-dev-deps python3 -m unittest discover -s .agents/skills/agy-search/tests -v
bash -n install-mcp.sh
./install-mcp.sh --dry-run
git diff --check
```

- MCP 테스트: 8개 예정(backend/unit + direct MCP client integration). 마지막 전체 재실행은 display HTML normalizer 테스트 추가 직전 7개 backend + 1개 server였으므로, 재개 시 위 전체 명령을 반드시 한 번 더 실행한다.
- Retained legacy contract test: 9개 통과.
- 실제 stdio child server의 MCP handshake와 `agy_search`, `agy_fetch` list-tools 통과.
- 실제 AGY fetch: `_workspace/agy-search/mcp-live-fetch/runs/agy_745c41a432104e56/`, 약 27초, `agy_read_artifact`, `partial`, provenance pass.
- 실제 AGY quick search: `_workspace/agy-search/mcp-live-search/runs/agy_026bdf1b5ff64127/`, 약 65초, python.org 3 URL을 반환하고 각 URL read, provenance pass.

위 `_workspace/` 증거는 gitignore이며 새 checkout에 없을 수 있다. 없다고 과거 trace를 만들어 넣거나 덮어쓰지 않는다.

## 중요한 한계와 안전 경계

- AGY `read_url_content` 원문은 stable public API가 아닌 conversation artifact(`content.md`)로만 관찰됐다. server는 AGY event가 가리킨 해당 conversation의 안전한 경로만 읽고, 없으면 `agy_generated_extract`로 명확히 라벨링한다.
- Mechanical provenance pass는 주장 진실성을 보장하지 않는다. 답변 생산자는 중요한 주장을 1차 출처로 독립 확인해야 한다.
- `--sandbox`와 사후 dangerous-tool audit는 사전 tool allowlist 증명이 아니다. AGY custom agent 제한은 #585 관련 불확실성 때문에 현재 사용하지 않는다.
- request 취소는 POSIX process group을 종료하고 trace/run metadata를 보존하도록 구현·테스트됐다. 실제 AGY auth failure, permission wait, outer timeout, Windows child-tree cleanup은 아직 live 검증하지 않았다.
- 설치 스크립트의 PowerShell 경로는 작성됐지만 Windows host에서 실행 검증하지 않았다.

## 재개 순서

1. `git status --short --branch`, `git diff --check`, `agy --version`, `agy models`로 상태와 인증을 다시 확인한다.
2. 위 전체 test 명령을 실행해 display normalizer 추가 뒤의 8개 MCP 테스트를 확정한다.
3. 다음 우선순위는 [plan.md](plan.md)의 P4: 약 20개 representative query fixture/scorecard를 만들고, query 개선·depth·언어·domain filter 효과를 표본 원문으로 평가한다.
4. 사용자가 실제 등록을 요청하면 `./install-mcp.sh`를 실행한다. 이 명령은 user Python site와 Codex config를 변경하므로 dry-run 결과와 기존 `codex mcp get agy-search` 상태를 먼저 확인한다.
5. 구현을 바꾸면 README/plan/handoff도 함께 갱신하고, 검증 후에만 commit/push 여부를 결정한다.

## 기존 조사 요약

AGY 1.2.7에서 `search_web`는 Google Search, `read_url_content`는 페이지 취득을 수행한다. Headless `stream-json`의 완료 tool event에는 parameter는 있으나 결과 본문이 없는 사례가 있었고, `view_file`가 가리킨 `content.md`에 HTML 포함 원문이 저장된 사례가 있었다. terminal `structured_output`은 사용 가능하지만 생성 결과이므로 원문과 구별한다. 상세 출처와 평가 설계는 [조사·설계 기록](docs/agy-search-mcp-plan.ko.md)을 참조한다.
