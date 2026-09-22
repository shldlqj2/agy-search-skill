# AGY Search MCP

한국어 | [English](README.md)

`agy-search-mcp`는 로컬 Antigravity CLI(`agy`)를 Codex의 로컬 MCP 도구 두 개로 노출합니다.

- `agy_search`: 현재 웹을 검색하고, 같은 요청에서 AGY가 실제로 연 URL만 반환
- `agy_fetch`: `agy_search`가 반환한 `source_id` 또는 하나의 URL을 AGY로 읽기

웹 검색과 신규 페이지 읽기는 오직 AGY가 수행합니다. Codex 내장 검색으로 자동 전환하지 않습니다.

## 왜 스킬 대신 MCP인가

기존 스킬은 Codex 프롬프트 안에서 검색·검토·합성을 조율했습니다. MCP 전환 후에는 경계가 분명한 검색 작업을 일반 로컬 코드가 처리합니다. 도구 호출 하나가 sandbox AGY 자식 프로세스 하나를 시작하고 직접 종료까지 기다린 뒤 최종 결과를 반환합니다. Codex 서브에이전트, watcher, 완료 상태 폴링, 모델 기반 재시도 루프를 만들지 않습니다.

AGY는 결정론적 검색 인덱스가 아니라 생성형 에이전트입니다. 따라서 서버는 요청별 NDJSON trace를 보존하고, AGY가 검색하고 반환 URL을 같은 실행에서 모두 읽지 않으면 검색 결과를 거부합니다. 위험 도구 사용도 거부합니다. 이 provenance 검사는 출처 연결을 검증할 뿐 내용의 진실을 보장하지 않으므로, 중요한 주장은 1차 출처로 별도 확인하세요.

## 요구 사항

- 로컬 stdio MCP를 지원하는 Codex CLI
- `PATH`에서 실행되고 인증된 `agy` (`agy models` 성공)
- Python 3.10 이상과 `pip`
- Linux/macOS의 Bash 또는 Windows PowerShell

구현은 AGY 1.2.7 및 MCP Python SDK 2.2.0으로 실제 호출 검증했습니다.

## 설치

저장소 루트에서 MCP 설치기를 실행하세요. 선택한 Python의 사용자 site에 패키지를 설치하고 Codex에 `agy-search` 로컬 서버를 등록합니다. deep 요청이 종료될 수 있도록 Codex 도구 timeout도 660초로 설정합니다.

Linux/macOS:

```bash
chmod +x install-mcp.sh
./install-mcp.sh
```

Windows PowerShell:

```powershell
.\install-mcp.ps1
```

변경 없이 미리 보기:

```bash
./install-mcp.sh --dry-run
```

```powershell
.\install-mcp.ps1 -DryRun
```

기본 상태 경로는 Linux/macOS에서 `~/.local/state/agy-search-mcp`, Windows에서 `%LOCALAPPDATA%\agy-search-mcp`입니다. 이곳에는 trace와 작은 로컬 `source_id` 인덱스, 읽어 온 콘텐츠가 남을 수 있으므로 적절히 보호하세요. `--data-dir` 또는 `-DataDir`로 바꿀 수 있습니다.

등록 뒤 Codex를 재시작하거나 새 세션을 시작하세요. 기존 `agy-search` 스킬은 자동 삭제하지 않습니다. MCP가 정상 동작함을 먼저 확인한 뒤, 스킬 라우팅 혼선을 일으킬 때만 직접 제거하세요.

### 수동 등록

수동 설치가 필요하다면 Codex가 실행할 동일한 Python으로 패키지를 설치한 다음 등록합니다.

```bash
python3 -m pip install --user --upgrade .
codex mcp add agy-search \
  --env "AGY_SEARCH_MCP_DATA_DIR=$HOME/.local/state/agy-search-mcp" \
  -- python3 -m agy_search_mcp.server
```

`$CODEX_HOME/config.toml`(또는 `~/.codex/config.toml`)의 `[mcp_servers.agy-search]` 아래에 다음을 추가하세요.

```toml
startup_timeout_sec = 30
tool_timeout_sec = 660
```

## 도구 계약

`agy_search`는 자연어 `query`와 선택적 `max_results`(1–10), 도메인 allowlist, 선호 언어, 최신성 기준일, `depth`를 받습니다.

| depth | 기본 AGY 기한 | 용도 |
| --- | ---: | --- |
| `quick` | 180초 | 좁은 단건 조회 |
| `standard` | 300초 | 일반 조사 |
| `deep` | 600초 | 다중 출처·상충 검토 |

`timeout_seconds`(1–600)를 명시하면 이 정책을 덮어씁니다. 일반 검색의 기본값은 여전히 5분입니다. `agy_fetch`는 기본 5분이며 동일한 명시적 override를 지원합니다.

검색 결과에는 이 서버 상태 경로 안에서만 유효한 `source_id`, URL, 짧은 AGY 근거 기반 요약, 발췌, provenance가 있습니다. 페이지 내용을 더 읽을 때 이 ID를 `agy_fetch`에 전달하세요. `agy_fetch`의 본문은 다음처럼 구분합니다.

- `agy_read_artifact`: 해당 요청에서 AGY가 읽은 artifact에서 서버가 추출한 텍스트
- `agy_generated_extract`: 안전하게 사용할 artifact가 없을 때 AGY가 생성한 명시적 fallback

두 번째 항목을 원문 인용처럼 표현하면 안 됩니다. source ID는 상태 경로가 보존되는 동안만 유지되며, URL로는 언제든 AGY 재읽기를 요청할 수 있습니다.

서버는 한 번에 AGY 요청 하나만 실행합니다. 동시 요청은 숨은 대기열이나 polling 없이 명시적인 `busy` 오류를 받습니다. 의도적으로 `status`나 `poll` 도구는 제공하지 않습니다.

## 증거와 실패 처리

각 호출은 상태 경로 아래의 별도 디렉터리에 증거를 남깁니다.

```text
runs/<request_id>/
  trace.ndjson
  stderr.log
  run.json
  mcp-response.json
source-index.json
```

인증·권한·provenance·timeout·취소·프로세스 실패 시 부분 trace와 stderr를 보존합니다. 실패를 빈 검색 결과로 바꾸지 않고 구조화된 오류 결과로 반환하며, 서버가 AGY를 자동 재실행하지 않습니다.

웹 취득은 AGY만 담당합니다. 인용 형식과 핵심 주장 검토를 포함한 최종 답변 책임은 호출자에게 있습니다. 의료·법률·금융·보안 또는 되돌리기 어려운 결정을 위해서는 권위 있는 출처를 직접 확인하고 적절한 전문가 판단을 더하세요.

## 개발·검증

현재 환경에 패키지를 설치한 뒤 MCP 테스트와 유지 중인 legacy 계약 테스트를 모두 실행합니다.

```bash
python3 -m pip install --user -e .
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s .agents/skills/agy-search/tests -v
git diff --check
```

`agy models`로 인증을 확인한 뒤 로컬 stdio 서버를 직접 띄울 수 있습니다.

```bash
AGY_SEARCH_MCP_DATA_DIR=_workspace/agy-search/manual-mcp \
python3 -m agy_search_mcp.server
```

마지막 명령은 stdio 서버이므로 터미널에서 질의하지 말고 MCP 클라이언트로 연결하세요. `_workspace/agy-search/` 런타임 증거는 의도적으로 커밋하지 않습니다.

## 전환·프로젝트 문서

- [MCP 전환 설계와 조사 기록](docs/agy-search-mcp-plan.ko.md)
- [중단 후 이어갈 수 있는 실행 계획](plan.md)
- [현재 작업 인계](handoff.md)
- [legacy 스킬 실행 계약](.agents/skills/agy-search/references/team-spec.md)

legacy 스킬 소스는 호환성과 계약 테스트를 위해 `.agents/skills/`에 남아 있습니다. 기존 `install.sh` / `install.ps1`은 의도적으로 프롬프트 기반 스킬 흐름을 유지하려는 경우에만 사용하세요. 새 설치는 위 MCP 설치기를 사용하세요.
