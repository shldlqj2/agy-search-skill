# agy-search 스킬

한국어 | [English](README.md)

Codex에서 로컬 Antigravity CLI(`agy`)를 추적 가능한 웹 검색 백엔드로 사용하는 스킬입니다. AGY의 도구 실행 추적을 보존하고, 주장별 출처를 요구하며, 실제로 읽지 않은 페이지를 인용하면 결과를 거부합니다. 최종 합성 전에는 별도의 독립 검증 계약을 적용합니다.

## 왜 필요한가

에이전트는 자연스러운 답변을 만들면서 URL을 지어내거나, 실제로 존재하지만 읽지 않은 페이지를 인용하거나, 주장을 뒷받침하지 않는 관련 자료를 붙일 수 있습니다. `agy-search`는 AGY를 결정론적 검색 인덱스가 아니라 검증되지 않은 검색 생산자로 취급합니다.

하네스는 다음 책임을 분리합니다.

1. 질문의 범위와 최신성 기준 설정
2. AGY를 이용한 검색 및 원문 읽기
3. 출처 추적 감사와 원자적 주장 단위의 독립 검증
4. 검증된 주장만 합성하고 충돌과 불확실성 보존

이는 하나의 기본 Codex 에이전트 안에서 수행하는 논리적 단계이며, 별도의 Codex 서브에이전트가 아닙니다. 이 스킬은 서브에이전트 fan-out과 완료 감시 에이전트를 금지합니다. Codex가 AGY CLI 자식 프로세스 하나를 직접 실행하고 기다린 뒤, 같은 실행 안에서 검증과 합성을 완료합니다.

## 요구 사항

- 스킬 검색이 활성화된 Codex
- `PATH`에서 실행 가능한 Antigravity CLI `agy`
- 인증된 AGY 세션(`agy models`가 성공해야 함)
- Python 3
- Linux/macOS의 Bash 또는 Windows PowerShell

현재 실제 검증에 사용한 AGY 버전은 1.2.4입니다.

## 전역 설치

저장소를 복제한 뒤 루트에서 설치 스크립트를 실행합니다. `agy-search`와 `agy-search-verifier`가 함께 Codex 전역 스킬 디렉터리에 설치됩니다.

Linux/macOS:

```bash
chmod +x install.sh
./install.sh
```

Windows PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install.ps1
```

기본 설치 위치:

- `CODEX_HOME`이 설정되어 있으면 `$CODEX_HOME/skills`
- Linux/macOS에서는 그 외의 경우 `~/.codex/skills`
- Windows에서는 그 외의 경우 `$HOME\.codex\skills`

테스트용 사용자 지정 경로:

```bash
./install.sh --target /tmp/codex-skills --dry-run
```

```powershell
.\install.ps1 -Target C:\temp\codex-skills -DryRun
```

기존 설치본은 교체 전에 타임스탬프가 붙은 경로로 백업됩니다. 복구 가능성을 의도적으로 포기할 때만 `--no-backup` 또는 `-NoBackup`을 사용하세요. 설치 후 Codex를 재시작하거나 스킬을 다시 로드해야 할 수 있습니다.

이 스킬의 전역 설치 대상은 Codex입니다. AGY 자체의 스킬 디렉터리에는 설치하지 마세요. 이 스킬은 `agy`를 외부 백엔드로 호출하므로 AGY 내부에 설치하면 실행 경계가 잘못됩니다.

## 사용법

자연어로 요청하거나 명시적으로 호출할 수 있습니다.

```text
$agy-search 최신 안정 Python 릴리스를 찾고 공식 릴리스 페이지로 검증해줘.
```

설치된 스킬 디렉터리에서 어댑터를 직접 실행할 수도 있습니다.

Linux/macOS:

```bash
python3 ~/.codex/skills/agy-search/scripts/agy_search.py \
  --out-dir _workspace/agy-search/python-release \
  --query "현재 최신 안정 Python 릴리스는 무엇인가?"
```

Windows PowerShell:

```powershell
py -3 "$HOME\.codex\skills\agy-search\scripts\agy_search.py" `
  --out-dir "_workspace\agy-search\python-release" `
  --query "현재 최신 안정 Python 릴리스는 무엇인가?"
```

## 환각 방어

기계적 감사는 다음 조건을 요구합니다.

- 성공한 터미널 결과
- 완료된 `search_web` 및 `read_url_content` 호출
- 선언된 모든 출처 URL과 실제 완료된 읽기 호출 URL의 정확한 일치
- 모든 사실 주장에 선언된 출처 ID 연결
- 답변 인용에 선언된 출처만 사용
- 명령, 파일 쓰기, MCP, 예약 작업, 서브에이전트 도구 미사용
- JSON Schema를 만족하는 결과와 보존된 NDJSON 추적

기계적 통과는 출처 연결의 일관성을 증명할 뿐, 내용의 진실성을 증명하지 않습니다. `agy-search-verifier`가 원문을 다시 열고 각 주장을 `supported`, `contradicted`, `insufficient`로 판정해야 합니다. 의료·법률·금융·보안 또는 되돌릴 수 없는 결정에는 권위 있는 자료와 자격을 갖춘 사람의 검토가 필요합니다.

## 산출물

각 실행은 `_workspace/agy-search/<run>/` 아래에 결정론적인 핸드오프 파일을 남깁니다.

```text
00_request.md
01_trace.ndjson
01_result.json
01_stderr.log
02_verification.md
final.md
```

원본 추적은 감사 증거입니다. 실패한 실행을 통과시키기 위해 수정하면 안 됩니다.

## 검증

```bash
python3 -m unittest discover -s .agents/skills/agy-search/tests -v
```

닫힌 지식만 사용한 답변, 읽지 않은 URL, 존재하지 않는 출처 ID, 누락·그룹 인용, 위험 도구 사용을 검사하는 계약 테스트가 포함됩니다. 정상 최신정보 질의와 조작된 전제에 대한 실제 카나리도 수행했습니다.

## 알려진 AGY 제약

AGY CLI 1.2.4에서 [google-antigravity/antigravity-cli#585](https://github.com/google-antigravity/antigravity-cli/issues/585)가 재현됐습니다. 요청한 워크스페이스 커스텀 에이전트를 찾지 못하고 기본 에이전트로 조용히 대체될 수 있습니다. 따라서 현재 러너는 기본 에이전트를 `--sandbox`에서 실행하고 넓은 도구 노출을 보고하며, 위험 도구가 실제 사용되면 결과를 폐기합니다. 제한된 커스텀 에이전트 어댑터는 `init.tools`가 정상 로드를 증명할 때까지 비활성 상태입니다.

전체 설계는 [팀 계약](.agents/skills/agy-search/references/team-spec.md), [환각 방어 규칙](.agents/skills/agy-search/references/hallucination-control.md), [검증 기록](docs/harness/agy-search/validation.md)을 참고하세요.
