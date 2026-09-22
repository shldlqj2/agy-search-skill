# AGY 검색 MCP 조사 및 구현 계획

작성일: 2026-09-22. 상태: 조사 기반 설계안과 1차 구현 기록. 기본 MCP server는 구현·검증됐고, 품질 평가와 실제 사용자 등록은 남아 있다.

## 목표와 경계

Codex가 검색 도구 한 번을 호출하면 AGY가 검색하고 필요한 자료를 읽어 짧고 출처가 연결된 결과를 반환한다. 검색과 새 페이지 취득은 AGY만 수행하며 Codex 내장 검색이나 별도 검색 서비스로 자동 전환하지 않는다. 서버는 AGY가 취득한 자료를 파싱·정규화·보관하는 일반 Python 프로그램이다.

AGY 토큰 비용은 최적화 목표에서 제외한다. 검색 품질, Codex의 도구 호출 횟수와 응답 크기, 대기 중 모델 호출 제거를 우선한다. Codex 서브에이전트, watcher, 상태 조회용 폴링 API는 만들지 않는다. 이 조사에서 사용한 별도 웹 열람은 문서 독립 검증 수단이며 제품의 검색 경로가 아니다.

## 확인한 근거

| 구분 | 확인 내용 | 설계에 미치는 영향 |
| --- | --- | --- |
| 로컬 확인 | `agy --version`은 1.2.7. `agy models` 정상 완료 | 기존 1.2.4 기록과 구분하고 설치 버전별 호환성 검사 |
| 공식 문서 | `search_web`은 Google Search, `read_url_content`는 URL 취득 도구 [S1] | AGY가 실제 검색·읽기를 담당 |
| 공식 문서 및 CLI 도움말 | headless, NDJSON, terminal structured output, timeout 지원 [S2] | MCP 서버가 이벤트를 읽고 최종 응답을 반환 |
| 기존 실행 산출물 관찰 | search_web의 output.txt가 출처가 붙은 요약문이고 grounding redirect URL을 포함 | Google 원본 SERP 순위·정확한 제목·검색 스니펫을 그대로 제공한다고 약속하지 않음 |
| 기존 실행 산출물 관찰 | NDJSON에서 검색·읽기 output이 빠진 사례. content.md 안에 원시 HTML 저장 사례 | stream만으로 원문 추출이 가능한지 실험하고 명시적 산출물 어댑터 준비 |
| 공식 문서 | SDK enabled_tools/disabled_tools 제공 [S1] | CLI 제한이 불충분하면 SDK를 비교 후보로 검토. 인증·산출물 접근 동등성은 별도 검증 |
| 외부 이슈 및 로컬 확인 | #585가 열려 있고 로컬 `agy agents`가 목록 없이 종료 [S3] | 커스텀 agent가 정상 로드됐다고 가정하지 않음. 현재 버전 재현 테스트 필요 |
| 공식 MCP 규격 | 진행 통지와 취소 통지 정의 [S4][S5] | 지원 클라이언트에서 이벤트 기반 진행·취소 제공. 진행 통지가 timeout 연장을 보장하지는 않음 |

로컬 관찰 근거는 `_workspace/agy-search/live-canary-4/01_trace.ndjson` 및 해당 conversation의 `.system_generated/steps/2/output.txt`, `steps/4/output.txt`, `steps/4/content.md`이다. 내부 디렉터리 구조는 공개 안정 API로 취급하지 않는다. 다른 설치에서도 동일하다는 보장은 없다.

이번 1.2.7 실제 조사 실행도 약 266초에 SUCCESS로 종료했고 search_web 9회, read_url_content 19회, view_file 24회를 수행했다. 검색·읽기 완료 이벤트의 tool_info에는 name/parameters만 있었고 output은 없었다. 기계적 감사는 통과했지만 독립 원문 검토에서 일부 주장은 근거 부족 또는 잘못된 해석이었다. 특히 AGY가 인용한 CLI Reference에는 주장한 검색 도구 파라미터 설명이 없었고, #837은 소비자 디코더 문제가 아니라 AGY가 이미 손상된 delta를 출력한 과거 이슈였다. 최종 result는 온전했다는 보고가 있으므로 최종 structured_output을 우선하고 delta는 진행 표시용으로 제한한다 [S7]. 현재 버전의 동일 버그 재현 여부는 미확인이다.

## 2026-09-22 구현 기록

`src/agy_search_mcp/`에 MCP Python SDK 2.2.0 기반 stdio server를 구현했다. `agy_search`는 AGY의 `search_web`과 반환 URL 전체의 `read_url_content`를 같은 실행에서 요구하고, `agy_fetch`는 요청한 URL의 `read_url_content`만 요구한다. 둘 다 terminal SUCCESS, parseable structured output, 위험 도구 미사용을 검사한다. 요청 하나는 AGY child process 하나를 직접 기다린다. 서버가 별도 Codex agent, completion watcher, `status`/`poll` 도구, 자동 재시도를 만들지 않는 것이 의도된 동작이다.

timeout은 quick 180초, standard 300초, deep 600초이며 명시 override는 1–600초다. 동시 AGY 실행은 하나로 제한하고 대기열 대신 `busy` 오류를 반환한다. 취소 시 POSIX process group을 종료하고 trace·stderr·run metadata를 보존하는 subprocess test를 통과했다. 실제 AGY `fetch`(약 27초, artifact text)와 `quick search`(약 65초, python.org 3 URL 모두 read)도 provenance gate를 통과했다. 증거 경로는 [plan.md](../plan.md)에 있다.

원문 artifact 경로는 안정 공개 API가 아니므로, 서버는 AGY event가 가리킨 해당 conversation 경로만 제한적으로 읽고 반환 길이만큼 텍스트화한다. 원본 파일을 별도로 복제하거나 raw content hash를 API 계약으로 노출하지 않는다. artifact가 없으면 생성 fallback을 `agy_generated_extract`로 명시한다. 따라서 아래 설계안 중 “원본 및 hash 보존”은 향후 안정 취득 API가 확보될 때만 재검토할 항목이다.

## 검색 품질 전략: 구현 후 비교 검증할 가설

1. 사용자 질문을 엔터티·버전·지역·기준일·원하는 근거로 구조화한다. 원 질문을 보존하고 모호함을 조용히 덮어쓰지 않는다.
2. 넓은 검색으로 후보를 찾은 후 공식 도메인·정확한 제품명·버전·오류 문구로 좁힌다. 기술 질문은 필요할 때 한국어와 영어 쿼리를 함께 사용한다. 번역으로 고유명사와 버전 조건을 바꾸지 않는다.
3. `site:`, 인용부호, 제외어, 날짜 연산자를 검색어 후보로 활용한다. Google의 연산자 문서 [S6]는 근거지만 AGY가 모두 그대로 적용한다는 증거는 아니다. 실제 결과의 도메인·날짜를 다시 검사한다.
4. `standard` 모드는 상위 후보의 핵심 페이지를 AGY가 읽고 관련 구절을 함께 반환한다. Codex의 검색→페이지별 호출 반복을 줄이는 것이 목적이다.
5. 비교·논쟁·최신 변경 사항은 서로 다른 출처 및 반대 근거를 탐색한다. 같은 발표를 복제한 여러 문서를 독립 근거로 세지 않는다.
6. 최신성은 검색일, 문서 게시·수정일, 사건일, 적용 버전을 구분한다. 날짜가 없으면 null로 남긴다. 'latest'를 쿼리에 넣는 것만으로 최신성이 입증되지는 않는다.
7. 정해진 결과 개수를 채우려고 항목을 만들지 않는다. 부족한 결과와 접근 불가·상충 근거를 명시한다.
8. 결과가 충분하면 종료하고, 부족하면 AGY 한 실행 안에서 쿼리를 수정한다. CLI 재시작 재시도와 실행 내부의 다회 검색을 구별한다.

이 전략은 아직 성능 비교가 끝난 사실이 아니다. 아래 평가에서 단순 검색과 비교해 채택한다.

## MCP 도구 계약

### search

필수 인자: `query` 하나. 선택 인자는 `max_results`(기본 5, 상한 10), `depth`(`quick|standard|deep`, 기본 standard), `domains`, `language`, `as_of`, `timeout_seconds`, `fresh`.

- quick: 검색과 후보 출처 반환. 본문 읽기 보장을 하지 않음.
- standard: 검색어 개선과 주요 페이지 읽기를 포함. AGY에서 충분히 처리한 뒤 짧은 결과 반환.
- deep: 비교·상충 근거·복합 질문을 더 탐색. 긴 보고서를 기본 반환하지 않음.
- depth는 자체 정책이며 AGY의 모델/effort와 같은 개념이 아니다. 모델 매핑은 실험 후 결정.
- domains는 반환 URL을 서버가 정확한 도메인 경계로 검사한다. language는 선호 조건이다. as_of는 조사 기준일이며 과거 웹 상태 복원 기능이 아니다.

응답: `request_id`, `status`(ok/partial/no_results), `results`, `gaps`, `retrieved_at`. 항목은 안정적인 `source_id`, `title`, `url`, 짧은 `summary`, 선택적 `evidence_excerpt`, `published_at`, `read_status`, `provenance`를 가진다. provenance는 검색 도구 요약에서 유래했는지, 페이지를 실제 취득했는지, 요약이 생성됐는지를 구별한다. 서버가 확인한 실행 쿼리와 상세 감사는 로컬 artifact에 보관한다.

Google 원본 SERP임을 암시하는 rank나 원본 snippet 필드는 확보된 경우에만 제공한다. 생성 요약을 원문 인용으로 표시하지 않는다. 발췌는 추출 원문과 대조할 수 있을 때만 제공한다. 출처 연결 확인은 주장 진실성의 독립 검증과 같지 않다.

### fetch

입력: `url` 또는 기존 `source_id`, 선택적 `focus`, `offset`, `max_chars`, `fresh`, `timeout_seconds`.

이미 search에서 AGY가 읽은 문서는 저장한 본문에서 제공한다. 없는 문서는 AGY read_url_content로 취득한다. 응답에 읽기 시각, 원 요청 URL, 확인 가능한 최종 URL, 본문 형식, 잘림 여부, 다음 offset을 포함한다. focus는 관련 구절 선택용이며 원문 재작성 지시가 아니다. 본문을 확보하지 못하면 생성 요약을 본문으로 대체하지 않는다.

MVP 도구는 두 개만 제공한다. health 진단은 CLI 명령으로 제공하고 모델용 status/wait/research 별도 도구는 추가하지 않는다. 서버 tool description에 일반 검색·원문 읽기 용도와 예시를 적어 스킬 없이 사용할 수 있게 한다.

## 데이터 및 실행 구조

`Codex → MCP search/fetch → Python supervisor → AGY CLI → AGY web tools → artifact 정규화 → MCP 응답`

- MCP 서버는 상주 프로그램, AGY는 요청별 실행을 기본으로 한다. unrelated query에 `--continue`를 사용하지 않는다.
- asyncio subprocess로 stdout NDJSON과 stderr를 동시에 소비하고 trace를 즉시 저장한다. 기존 capture_output 방식은 실행 중 trace를 저장하지 못하므로 교체한다.
- 서버 stdout은 MCP 전용, 로그는 stderr/파일. 초기 handshake에서 긴 검색이나 로그인을 실행하지 않는다.
- NDJSON 바이트 스트림은 온전한 행을 조립한 뒤 UTF-8로 디코딩한다. 최종 데이터는 terminal structured_output과 취득 artifact를 사용하고 text_delta 연결로 복원하지 않는다. 한글·이모지 분할과 이미 손상된 delta를 별도 fixture로 검사한다 [S7].
- 기한 기본 300초, 호출자가 600초 이내 조절. 실행 전에 depth에 따라 제안하되 선택한 기한을 기록하고 실행 중 몰래 연장하지 않는다. AGY 기한, 서버 정리 시간, MCP 클라이언트 기한을 정렬한다.
- 진행 통지는 실제 단계 변화에 맞춰 제한적으로 보낸다. 완료 대기는 I/O 대기로 처리하고 LLM을 다시 깨우지 않는다. 실제 클라이언트 동작은 수용 테스트로 확인한다.
- 취소, 연결 종료, timeout 시 프로세스 트리 정리와 stderr/부분 trace 보존. 실패를 빈 검색 결과와 구분한다.
- 기본 동시 실행 1. 대기 요청도 deadline에 포함하고 과부하는 명시적 오류로 반환한다.
- AGY 실행 내부 검색 횟수는 품질과 기한으로 제어한다. 자동 CLI 재실행은 기본 비활성화. 복구 가능 오류에 한해 전체 기한 안에서 최대 1회로 설계하며 인증/권한 실패에는 재시도하지 않는다.
- fresh는 서버 캐시 우회일 뿐 AGY/상류 캐시까지 우회한다고 보장하지 않는다. 본문 캐시는 검색 결과와 같은 조회 시각을 표시한다.

## 원문 어댑터와 제약

우선순위는 공개 이벤트의 실제 output → 실행 ID/step에 연결된 산출물 → 명시적으로 표시한 생성 요약이다. 실제 내용이 없는 경우 내용을 추측하지 않는다.

산출물 읽기는 해당 요청의 conversation/step 디렉터리로 제한하고 경로 정규화·심볼릭 링크 경계를 검사한다. 검색 결과에 포함된 임의 로컬 경로를 열지 않는다. 원문 HTML은 서버에서 반환 길이만큼 텍스트로 추출하며, 현재 불안정한 내부 artifact를 별도 복제하거나 raw content hash를 API 계약에 넣지 않는다. grounding URL과 해결된 URL은 관찰된 경우에만 구분하고, redirect 추적은 AGY에서 수행하며 관찰되지 않은 canonical URL로 대체하지 않는다.

커스텀 agent를 사용하려면 init.tools가 실제 제한 목록임을 검증한다. `--sandbox`는 웹 전용 allowlist와 동치가 아니고, 사후 감사도 실행 전 차단과 동치가 아니다. CLI에서 원하는 제한을 보장할 수 없으면 제약을 명시하고 SDK capabilities와 사전 hook 대안을 실험한다. SDK에서도 검색 엔진은 AGY이며 Codex 내장 검색은 사용하지 않는다.

## 구현 단계와 통과 조건

1. **호환성 실험**: AGY 1.2.7에서 검색/읽기/원문 산출물/커스텀 agent/취소/timeout 확인. 단계별 원본 fixture 확보. 원문 추출 경로가 불확실하면 full-text 제공을 약속하지 않음.
2. **backend 분리**: 기존 parser/audit 재사용, async supervisor와 artifact store, 검색용/읽기용 개별 schema·gate 구현. 현재 모든 호출에 search와 read 둘 다 요구하는 gate는 용도별로 분리.
3. **MCP 서버**: 공식 Python MCP SDK 사용, search/fetch, 오류·취소·진행·길이 제한 구현. 의존성 버전 고정.
4. **품질 실험**: 단일 쿼리 대비 쿼리 개선+선행 읽기, 한국어 단독 대비 한국어+영어, 사용 가능한 모델/effort 비교. AGY 토큰 비용은 선택 기준에서 제외.
5. **전환**: 설치 스크립트, MCP 등록 안내, 한·영 README, repository guide 변경. 기존 skill은 legacy로 분리하고 기존 사용자 설정과 설치본은 백업 가능한 이행 절차 제공.
6. **종단 검증**: 스킬 없는 새 클라이언트 세션에서 자연어 요청→MCP→AGY→출처 답변을 확인. 내장 검색 fallback, Codex subagent, status polling이 없어야 함.

## 평가 설계

약 20개 질의를 구성한다: 공식 최신 릴리스, 버전 지정 기술 문제, 한국어 지역 정보, 비교, 상충 주장, 날짜 경계, 가짜 전제, 존재하지 않는 URL, 긴 HTML/PDF, 접근 제한. 변동성이 있으므로 날짜를 고정한 fixture 검사와 live 평가를 구분하고 대표 질의는 반복 실행한다.

평가 항목: 상위 5개 관련 출처 비율, 핵심 질문 coverage, URL 출처 연결, 실제 읽은 페이지 비율, 발췌와 원문 일치, 날짜 조건 충족, 충돌/불충분 감지, Codex 호출 수·반환 문자수, 실행 시간 p50/p95. 의미적 평가는 사람이 표본 원문을 확인한다. 아직 우수 모델이나 개선률을 주장하지 않는다.

필수 통과: 반환 URL 출처 연결 100%, 원문 아닌 내용을 원문으로 표시한 사례 0, 알려진 위조 fixture 수용 0, 작업별 trace 충돌 0, 취소 후 잔존 AGY 프로세스 0, 스킬 없는 호출 성공. 일반 질의의 기본 목표는 search 1회, 추가 원문이 필요하면 fetch만 사용. 현재 연구는 설계 조사이며 이 평가가 완료된 것은 아니다.

## 출처

- S1: https://antigravity.google/docs/sdk/tools/ — 웹 도구와 capabilities.
- S2: https://antigravity.google/docs/cli/headless/ — NDJSON, schema, 세션, timeout, 권한.
- S3: https://github.com/google-antigravity/antigravity-cli/issues/585 — agent discovery 문제 보고. 현재 설치에서 동일 원인 확정은 아님.
- S4: https://modelcontextprotocol.io/specification/2025-06-18/basic/utilities/progress — 진행 통지.
- S5: https://modelcontextprotocol.io/specification/2025-06-18/basic/utilities/cancellation — 요청 취소.
- S6: https://support.google.com/websearch/answer/2466433?hl=en — Google 검색 연산자. AGY 파라미터 보장은 아님.
- S7: https://github.com/google-antigravity/antigravity-cli/issues/837 — 구버전 delta 손상 보고. 종료된 이슈이며 최신 버전에 일반화하지 않음.

실행 증거와 별도 검증 기록: `_workspace/agy-search/mcp-research/`.
