# RecomEngine — Gemma 로컬 AI 환경 구성 및 팀원 테스트

2026-11-27 기준 · Windows · 기존 팀원 공통 테스트본 기반 Context Fix (중간 테스트본)

## 1. 기존 AI 담당자: 모델만 변경하면 됩니다

> 본인 PC의 Ollama와 Cloudflare Tunnel/Worker 연결이 이미 정상이라면 Cloudflare를 다시 만들 필요가 없습니다. 기존 Worker가 본인 PC의 Ollama(127.0.0.1:11434)를 바라보고 있는지 확인하세요.

CMD에서 순서대로 실행합니다.

```cmd
ollama --version
ollama pull gemma4:12b
ollama list
ollama run gemma4:12b
```

추천 질문을 입력해 응답을 확인한 뒤 `/bye`로 대화 세션을 종료합니다. Ollama 앱/서버는 계속 실행해 둡니다. 기존 Qwen 삭제는 필수가 아니며, 더 이상 필요하지 않을 때만 `ollama rm qwen2.5:7b`를 실행합니다.

Worker가 모델을 고정하지 않고 요청을 전달하는 기존 구조라면 Worker 코드도 변경할 필요가 없습니다. 아래 공통 통합본은 요청 모델을 gemma4:12b로 지정합니다. 본인 Worker에서 인증을 포함한 /api/tags 조회로 새 모델이 보이는지 확인하세요.

## 2. 팀원 공통 테스트본

- 파일명: **RecomEngine_Gemma_Team_Test_ContextFix.zip**
- [GitHub Releases — 공통 ZIP 배포 위치](https://github.com/esse040402-star/recomengine-backend/releases)
- ZIP 첨부 상태: 아직 업로드 대기. 팀장이 공통 ZIP을 Releases에 첨부하면 해당 파일 하나를 내려받아 사용합니다. 팀원별 별도 빌드나 테스트본 제작은 필요 없습니다.
- SHA-256: `b76f6b3e4f8aa5d9bf592964e05d818a15bafb10738a829dad045084db0d5ad1`

> **2026-11-27 수정 사항:** Steam TOP 100 조건부 추천에서 발생한 HTTP 400(프롬프트 길이 초과)을 해결하기 위해 `runtime/app/services/ollama.py`의 `structured_chat`에 전달하는 `num_ctx`를 16384로 변경했습니다. 일반 `natural_chat`과 기존 `chat_json`은 8192를 유지합니다. 이미 환경을 구성한 팀원은 새 ZIP만 받아 실행하면 되며 모델이나 Cloudflare를 다시 설정할 필요가 없습니다. GPU/VRAM/RAM에 따른 성능 차이는 있을 수 있습니다.

### 실행 순서

1. [Python Windows](https://www.python.org/downloads/windows/)에서 Python 3 및 Python Launcher(py)를 설치하고 `py -3 --version`을 확인합니다.
2. Ollama 앱을 실행하고 `curl http://127.0.0.1:11434/api/tags`에서 gemma4:12b가 있는지 확인합니다.
3. ZIP 전체를 새 폴더에 압축 해제하고 기존 RecomEngine 서버를 종료합니다.
4. `START_AI_TEST.cmd`를 더블 클릭합니다. 첫 실행 시 가상환경과 Python 의존성을 설치하므로 인터넷이 필요합니다.
5. 연결 방식 선택: **1 또는 Enter = 같은 PC의 Ollama 직접 연결(권장, 인증키 불필요)**. **2 = 본인 Cloudflare Worker 연결(HTTPS 주소와 해당 Worker의 AI_API_KEY 입력)**. 인증키 입력 중 문자가 보이지 않아도 정상입니다.
6. 브라우저가 열립니다. 기본 주소는 http://127.0.0.1:8012/ 이며 포트 충돌 시 CMD에 출력되는 실제 주소를 사용합니다.
7. 웹에서 AI 게임 추천을 테스트합니다. 서버 종료는 실행 CMD에서 Ctrl+C, Ollama는 테스트 중 유지합니다. 원격 방식에서는 Tunnel도 유지합니다.

| 구분 | 같은 PC 테스트 | 외부 서버/Cloudflare 경유 테스트 |
|---|---|---|
| Ollama + Gemma | 필요 | AI 호스트 PC에 필요 |
| Cloudflare | 불필요 | 필요 |
| 연결 주소 | http://127.0.0.1:11434 | 본인 Worker HTTPS 주소 |
| AI_API_KEY | 불필요 | 본인 Worker Secret과 동일 |
| 공통 ZIP | 동일 | 동일 |

기존 Chat Demo r1은 특정 Worker 주소가 고정되어 있어 각자 로컬 Ollama를 자동으로 사용하지 않았습니다. 이번 공통본은 기존 연결 선택 기능을 유지하며 실시간 추천용 structured_chat의 컨텍스트를 8192에서 16384로 변경했습니다. 일반 자연어 대화·추천 판단·UI는 유지합니다. 테스트 모드는 mock DB를 사용하므로 실제 Supabase에 쓰지 않습니다. Steam/IGDB 등 외부 API 기능은 별도 네트워크 및 필요한 키에 영향을 받을 수 있습니다.

## 3. 처음 구성하는 팀원: Ollama 설치

1. [Ollama Windows 다운로드](https://ollama.com/download/windows)에서 설치 파일을 내려받아 설치합니다. GPU 드라이버도 정상 상태인지 확인합니다.
2. Ollama를 실행한 후 새 CMD에서 `ollama --version`을 확인합니다.
3. `ollama pull gemma4:12b`를 실행합니다. 모델은 약 8GB이며 모델 외에도 실행 메모리가 필요합니다. GPU/VRAM/RAM에 따라 속도는 달라집니다.
4. `ollama list`, `ollama run gemma4:12b`로 모델을 확인합니다.
5. 대화 확인 후 /bye로 종료합니다. 서버가 꺼져 있다면 Ollama 앱을 실행하거나, 이미 실행 중인 서버가 없는 경우에만 별도 CMD에서 `ollama serve`를 실행하고 유지합니다.
6. `curl http://127.0.0.1:11434/api/tags`로 로컬 API를 확인합니다. 추론 중 `ollama ps`로 모델 로드 및 CPU/GPU 사용 비중을 확인할 수 있습니다.

**같은 PC에서 웹을 실행하는 팀원은 여기까지 하고 2번의 공통 ZIP 실행 순서로 이동하면 됩니다.** Windows 방화벽에서 Ollama 포트를 인터넷에 개방하거나 OLLAMA_HOST를 0.0.0.0으로 변경할 필요가 없습니다.

## 4. 외부 서버 연동이 필요한 팀원: Cloudflare 처음부터 구성

기존 구현과 동일한 방식은 **Worker → VPC Service → Cloudflare Tunnel → Ollama**입니다. Workers VPC는 공식 문서 기준 베타이며 메뉴는 계정/UI에 따라 다를 수 있습니다. 이 VPC 방식은 별도의 사용자 도메인 구매 없이 Worker의 workers.dev 주소를 이용합니다.

### 4-1. Tunnel 설치 및 연결

1. [Cloudflare Dashboard](https://dash.cloudflare.com/)에 로그인합니다.
2. Networking → Tunnels (또는 Zero Trust → Networks → Tunnels)에서 Create Tunnel을 선택합니다.
3. Cloudflared 방식, 터널 이름 `recomengine-ai`를 선택하고 Windows 설치 안내를 엽니다.
4. 안내에 따라 cloudflared를 설치한 뒤 관리자 권한 CMD에서 `cloudflared --version`을 확인합니다.
5. 대시보드에 표시된 본인 토큰을 포함한 `cloudflared.exe service install <TUNNEL_TOKEN>` 명령을 실행합니다. 토큰은 GitHub나 채팅에 공개하지 않습니다.
6. 터널 상태가 Healthy/Connected인지 확인합니다. 기존 터널이 정상이라면 새로 만들지 않습니다.

### 4-2. Workers VPC Service 생성

터널의 Routes → Add route → Workers VPC 또는 Compute → VPC → VPC Services → Create service로 이동합니다.

| 설정 | 입력 |
|---|---|
| Service name | recomengine-ollama |
| Tunnel | 본인 recomengine-ai |
| Service type | HTTP |
| Host/IP address | 127.0.0.1 |
| Ports | Provide port values |
| HTTP Port | 11434 |
| HTTPS Port | 비워 둠 |
| TLS certificate verification | 기본값 유지 |
| DNS Resolver | IP 주소에서는 별도 설정 불필요 |

Ollama와 cloudflared는 같은 PC에서 실행합니다. Create service를 누릅니다.

### 4-3. Worker 및 Binding 생성

1. Compute → Workers & Pages → Create application → Start with Hello World에서 Worker를 만들고 Deploy합니다.
2. Worker의 Settings → Bindings → Add binding → VPC Service를 선택합니다.
3. Variable name: `OLLAMA`, VPC Service: `recomengine-ollama`로 선택하고 저장합니다.

### 4-4. 인증키 생성 및 Secret 설정

PowerShell에서 아래 명령으로 본인 키를 만들고 안전한 곳에 보관합니다.

```powershell
[guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N')
```

Worker → Settings → Variables and secrets → Add variable:
- Production 선택
- Key: AI_API_KEY
- Value: 본인이 생성한 키
- Secret 체크
- Add variable and deploy

Tunnel 설치 토큰과 Worker AI_API_KEY는 다른 값입니다. 기존 담당자는 본인의 기존 Secret을 사용할 수 있으며 공개된 키는 교체해야 합니다.

### 4-5. Worker 코드

Edit code에서 아래 예제 코드로 교체하고 Deploy합니다. 인증이 없는 요청은 거부하고, 필요한 Ollama API만 전달합니다. 공개 Ollama 포트를 만들지 않습니다.

```js
export default {
  async fetch(request, env) {
    if (!env.AI_API_KEY ||
        request.headers.get("Authorization") !== "Bearer " + env.AI_API_KEY) {
      return new Response("Unauthorized", { status: 401 });
    }
    const url = new URL(request.url);
    const allowed = {
      "/api/tags": "GET",
      "/api/chat": "POST",
      "/api/generate": "POST",
    };
    if (!Object.hasOwn(allowed, url.pathname))
      return new Response("Not Found", { status: 404 });
    if (request.method !== allowed[url.pathname])
      return new Response("Method Not Allowed", { status: 405 });
    try {
      return await env.OLLAMA.fetch("http://127.0.0.1:11434" + url.pathname, {
        method: request.method,
        headers: { "Content-Type": "application/json" },
        body: request.method === "POST" ? request.body : undefined,
      });
    } catch {
      return new Response("Ollama connection failed", { status: 502 });
    }
  }
};
```

이 코드는 개발 테스트용입니다. 공개 서비스 운영 시에는 추가 요청량 제한, 요청 크기 제한, 모델 허용 목록, 인증키 관리 등이 필요합니다.

### 4-6. Worker 연결 확인

CMD에서 아래 예시 주소를 본인 Worker 주소로 바꿉니다.

```cmd
set "WORKER_URL=https://YOUR-WORKER.YOUR-SUBDOMAIN.workers.dev"
curl -i "%WORKER_URL%/api/tags"
set /p AI_API_KEY=Enter your Worker key:
curl -i "%WORKER_URL%/api/tags" -H "Authorization: Bearer %AI_API_KEY%"
curl -i --max-time 180 "%WORKER_URL%/api/chat" -H "Authorization: Bearer %AI_API_KEY%" -H "Content-Type: application/json" -d "{\"model\":\"gemma4:12b\",\"messages\":[{\"role\":\"user\",\"content\":\"Recommend 3 story-driven PC games.\"}],\"stream\":false,\"think\":true}"
set "AI_API_KEY="
```

인증 없는 요청은 401, 인증한 모델 목록과 채팅 요청은 200을 기대합니다. 모델 목록에 gemma4:12b가 있어야 합니다. 이후 공통 ZIP 실행 시 2번을 선택해 같은 Worker 주소 및 인증키를 입력합니다.

## 5. Render에 연결하는 경우(참고)

Render는 팀원 PC의 localhost에 직접 연결할 수 없으므로 Worker HTTPS 주소를 사용합니다. 실제 배포는 별도 작업이며 이번 테스트는 로컬입니다.

| 서버 환경변수 | 값 |
|---|---|
| OLLAMA_ENABLED | true |
| OLLAMA_BASE_URL | 사용할 AI 호스트의 Worker HTTPS 주소 |
| AI_API_KEY | 해당 Worker의 Secret과 동일 |
| OLLAMA_MODEL | gemma4:12b |
| OLLAMA_TIMEOUT | 120 |
| OLLAMA_CONCURRENCY | 1 |
| OLLAMA_KEEP_ALIVE | 10m |

AI 호스트 PC, Ollama, Tunnel이 계속 작동해야 합니다. Render 환경변수나 Secret을 프론트엔드에 노출하지 않습니다. 팀원이 각자 Worker를 생성해도 단일 Render 서버가 자동으로 개인별 Worker를 선택하는 것은 아닙니다.

## 6. 테스트 질문 및 확인 기준

- 스토리가 좋고 몰입감 높은 싱글플레이 오픈월드 PC 게임 3개 추천해줘. 추천 이유는 게임마다 두 문장 이내로 설명해줘.
- 방금 추천한 3개는 모두 플레이했어. 같은 조건으로 다른 게임 3개 추천해줘.
- 그중 두 번째 게임은 어떤 내용이야?
- 이번에는 오픈월드가 아니어도 괜찮아. 스토리보다 전투가 재미있는 게임 3개 추천해줘.
- OneShot은 전투 중심 게임으로 적합하다고 생각해?
- 블루 아카이브 같은 서브컬처 게임 중 평가 좋은 게임 5~7개 추천해줘.
- 스팀 TOP 100 게임 중 액션 요소가 좋은 게임 5개만 추천해줘. (이번 컨텍스트 오류 재현 및 해결 확인)
- 현재 스팀 실시간 인기 게임 상위 10개 중 싱글플레이 게임을 추천해줘.
- 그럼 범위를 상위 100개로 넓혀서 싱글플레이 게임 중 유저평가가 좋은 게임 5개 추천해줘.
- 고마워. 이제 추천은 그만해도 돼.

대화 기억, 중복 제외, 조건 변경, 정확한 정보, 추천 카드, Markdown, 실시간 랭킹 및 실제 데이터 일치 여부를 확인합니다. 같은 모델이어도 생성 답변과 속도는 달라질 수 있습니다. 서버 실행 후 CHECK_GEMMA.cmd에 실제 웹 주소를 입력해 연속 질문 결과도 수집할 수 있습니다.

## 7. 오류 해결

| 증상 | 확인 |
|---|---|
| py 명령 인식 안 됨 | Python Launcher 설치, CMD 다시 열기 |
| Ollama 연결 안 됨 | 앱 실행 및 /api/tags 응답 확인 |
| 모델 없음 | ollama pull gemma4:12b |
| Worker 401 | 해당 Worker Secret과 입력 키 일치 여부 |
| Worker 502 | Ollama 실행, Tunnel Healthy, VPC Service 포트 및 Binding |
| 느린 응답/시간 초과 | ollama ps, GPU/RAM, 다른 모델/프로그램 사용량 확인 |
| TOP 100 요청에서 HTTP 400 / 웹 503 | ContextFix ZIP인지 확인. `ollama ps`로 structured_chat 요청 이후 CONTEXT 16384 확인. 긴 요청에서는 컨텍스트 초과가 다시 발생할 수 있음 |
| 구버전 화면 | 기존 서버 종료, CMD에 표시된 실제 주소 접속, Ctrl+F5 |

## 8. 현재 개발 상태

Gemma 자연어 대화 구조는 이전 사용자 테스트에서 개선됨을 확인했습니다. 초기 Natural Chat Test에서 실제 오류 응답 `the prompt is longer than the context length currently available to the model`을 확인했으며, structured_chat의 컨텍스트를 16384로 변경한 뒤 동일한 TOP 100 액션 게임 5개 추천 질문에 응답 및 카드 출력이 성공했습니다. 이번 공통본에도 동일한 수정을 적용했습니다. 관련 자동 테스트(모의 AI/API 포함) 42개 통과, Python 문법 검사 및 ZIP 무결성 검사 통과. 기존 공통본 대비 변경된 파일은 Ollama 통신 코드 1개, 테스트 2개, 안내 문서 1개입니다. 이번 ZIP 자체의 실제 Windows/Gemma/Worker 통신 및 브라우저 UI는 추가 검증이 필요합니다. 긴 요청에 대한 입력량 최적화 및 자동 복구, 실제 랭킹 일치 여부, UI 최종 검증, AI 심층설문 구현은 남아 있습니다.

## 9. 팀장: ZIP 배포 방법

1. [새 GitHub Release 작성](https://github.com/esse040402-star/recomengine-backend/releases/new)으로 이동합니다.
2. 새 태그 `gemma-team-context-fix`를 선택 또는 생성하고 대상 브랜치를 main으로 설정합니다.
3. Release title에 `Gemma 팀원 공통 테스트본 — Context Fix`를 입력합니다.
4. Attach binaries 영역에 `RecomEngine_Gemma_Team_Test_ContextFix.zip`을 첨부합니다.
5. 테스트 중간본이므로 필요하면 pre-release로 표시하고 Publish release를 누릅니다.
6. 팀원에게 [Releases 페이지](https://github.com/esse040402-star/recomengine-backend/releases)를 공유합니다.

ZIP 자체는 아직 GitHub에 첨부되지 않았습니다. 인증키 및 Tunnel 토큰은 ZIP이나 Release 설명에 넣지 않습니다. 같은 PC에서 직접 연결하는 1번 모드는 인증키가 필요하지 않습니다.

## 공식 문서

- [Ollama Windows](https://ollama.com/download/windows)
- [Gemma 4 모델](https://ollama.com/library/gemma4)
- [Cloudflare Tunnel](https://developers.cloudflare.com/tunnel/get-started/)
- [Cloudflare Workers VPC 시작하기](https://developers.cloudflare.com/workers-vpc/get-started/)
- [VPC Services](https://developers.cloudflare.com/workers-vpc/configuration/vpc-services/)
