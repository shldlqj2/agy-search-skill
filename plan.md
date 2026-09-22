# AGY 검색 MCP 실행 계획

최종 갱신: 2026-09-22
현재 단계: 기본 MCP 전환 구현·검증 완료. 다음 작업: P4 검색 품질 평가와 실제 사용자 환경 등록 확인.

재개 시 [handoff.md](handoff.md)를 먼저 읽고 실제 git 상태와 실행 중인 AGY 프로세스를 확인한다. 상세 조사 근거와 의도적 제약은 [조사·설계 기록](docs/agy-search-mcp-plan.ko.md)에 있다. 검증하지 않은 항목은 완료로 표시하지 않는다.

## 확정 요구사항

- 검색과 페이지 읽기는 AGY만 수행하며 Codex 내장 검색 fallback은 없다.
- AGY 토큰 비용보다 검색 품질과 Codex 호출·컨텍스트 부담 감소를 우선한다.
- Codex 서브에이전트, watcher, 모델 기반 완료 polling을 만들지 않는다.
- 한 MCP 호출은 AGY 자식 프로세스 하나를 직접 기다리고 최종 결과를 반환한다.
- normal 검색의 기본 timeout은 300초이며 `quick` 180초, `deep` 600초로 자동 조절한다. 명시 요청은 1–600초다.
- 사용자에게 스킬 실행 절차 대신 `agy_search`/`agy_fetch` MCP 도구를 제공한다.

## 단계별 상태

### P0 — 조사와 설계

- [x] 기존 runner/schema/audit 및 legacy 역할 계약 확인.
- [x] AGY 1.2.7 실제 조사 실행과 공식 문서 독립 검토.
- [x] 생성 요약·원문·trace의 차이와 불확실성 기록.
- [x] 상세 설계, 계획, 재개 문서 작성.
- [x] 구현 실험으로 CLI 명령·NDJSON·원문 artifact 접근·MCP SDK 2.2.0 사용을 확정.

### P1 — 호환성 실험

- [x] 요청별 별도 디렉터리에 실제 `fetch` 실행 기록: 2026-09-22, 약 27초, artifact 본문과 provenance gate 통과.
- [x] 실제 `search` 실행 기록: 2026-09-22, 약 65초, python.org 3개 URL을 모두 읽고 provenance gate 통과.
- [x] NDJSON terminal structured output과 AGY `content.md` artifact의 연결 및 HTML→텍스트 변환 확인.
- [ ] grounding redirect, PDF, 긴 본문, 한글 출력의 포괄 매핑 평가.
- [ ] 커스텀 agent의 실제 tool 제한을 `init.tools`로 입증. 현재는 의도적으로 사용하지 않는다.
- [x] 취소 시 child termination·부분 trace·`run.json` 보존을 fake AGY subprocess 테스트로 확인.
- [ ] 실제 AGY 인증/권한 실패와 outer timeout을 live 테스트. 정상 사용자 계정을 의도적으로 깨지 않는다.

### P2 — backend 분리

- [x] `src/agy_search_mcp/backend.py`에 parser/audit와 search/fetch별 provenance gate 분리.
- [x] async subprocess, stdout/stderr 동시 수집, 요청별 trace·응답 artifact 저장.
- [x] timeout, cancellation, POSIX process-group 정리, 오류 분류와 no-retry 정책.
- [x] source ID index, URL 대응, 길이 제한, HTML 텍스트화, artifact 경로 경계 확인.
- [x] artifact 원문과 AGY 생성 fallback을 `content_kind`로 구분.
- [x] 기본 동시 실행 1개와 명시적 `busy` 오류. 대기열·poll 도구 없음.

### P3 — MCP 서버

- [x] 고정된 MCP Python SDK 2.2.0과 stdio entry point 구현.
- [x] `agy_search(query)`와 `agy_fetch(url | source_id)` 구현.
- [x] query 개선·공식/1차 출처 우선·반환 URL 선행 읽기를 AGY 프롬프트 계약에 반영.
- [x] 짧은 결과, provenance, `ok`/`partial`/`no_results`/구조화 오류 구분.
- [x] direct MCP client와 실제 stdio handshake에서 도구 목록 확인. server stdout은 MCP protocol 전용.
- [x] cancellation은 child cleanup으로 처리. 호출 완료 polling과 별도 status 도구는 제공하지 않음.

### P4 — 검색 품질 평가

- [ ] 약 20개 평가 질의와 원문 판정 기준 작성.
- [ ] 단순 검색 대비 query 개선+선행 읽기 비교.
- [ ] 한글/영어 확장, 모델·effort, domain allowlist의 품질·지연 비교.
- [ ] 관련 출처, 발췌 정확성, 날짜, 상충 근거, 반환 크기, 실행 시간 p50/p95 기록.

완료 조건: 측정 근거로 기본 depth 정책을 조정한다. AGY 토큰 비용은 선택 기준에 넣지 않으며, 사전 평가 없이 모델 우열이나 개선률을 주장하지 않는다.

### P5 — 설치와 전환

- [x] `install-mcp.sh`/`install-mcp.ps1`, dry-run, Codex MCP 등록, 30초 startup·660초 tool timeout 설정 구현.
- [x] 기존 스킬을 자동 삭제하지 않는 안전한 migration 안내 작성.
- [x] 한·영 README와 `AGENTS.md`를 MCP 중심으로 갱신.
- [x] 새 stdio server process의 handshake·도구 목록 및 live AGY search/fetch 확인.
- [x] 새 MCP unit/in-process integration 테스트와 retained legacy contract 테스트 실행.
- [ ] 실제 사용자의 Codex config에 설치·등록. 사용자 환경을 변경하므로 별도 실행 시에만 한다.

## 검증 기록

개발 의존성을 repo-local `.mcp-dev-deps`로 둔 현재 작업 환경에서는 다음을 실행했다.

```bash
PYTHONPATH=src:.mcp-dev-deps python3 -m unittest discover -s tests -v
PYTHONPATH=src:.mcp-dev-deps python3 -m unittest discover -s .agents/skills/agy-search/tests -v
bash -n install-mcp.sh
./install-mcp.sh --dry-run
git diff --check
```

MCP 테스트 8개(backend, 취소, busy 정책, in-process handshake)와 legacy 계약 테스트 9개가 통과했다. 별도 stdio child process에서도 `agy_search`, `agy_fetch`의 handshake/list-tools를 확인했다.

Live evidence는 gitignore된 다음 위치에 있다.

- `_workspace/agy-search/mcp-live-fetch/runs/agy_745c41a432104e56/` — fetch, 약 27초, `agy_read_artifact`, `partial`, audit pass.
- `_workspace/agy-search/mcp-live-search/runs/agy_026bdf1b5ff64127/` — quick search, 약 65초, python.org 3개 반환·각 URL read, audit pass.

## 중단·재개 규칙

1. 중단 전에 이 파일과 `handoff.md`의 체크·검증·다음 한 행동을 함께 갱신한다.
2. 요청별 trace는 덮어쓰지 않는다. runtime evidence는 `_workspace/agy-search/` 또는 사용자 설정 state 경로에 보관하고 커밋하지 않는다.
3. 실행 중 작업이 있으면 PID, request ID, 로그 위치를 적는다. 재개 후 세션 핸들이 유효하다고 가정하지 않는다.
4. AGY timeout/cancel 시험에서 무관한 AGY 또는 다른 사용자의 프로세스를 종료하지 않는다.
