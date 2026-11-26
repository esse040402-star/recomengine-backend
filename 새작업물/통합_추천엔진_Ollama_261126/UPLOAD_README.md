# RecomEngine 통합본 GitHub 업로드 안내 (2026-11-26)

이 폴더는 전체 프로젝트 소스와 실행 자료를 정리한 업로드용 패키지입니다.

## 포함
- FastAPI 백엔드 및 Ollama 연동 코드
- React 프론트엔드 소스와 정적 원본 에셋
- 테스트, 데이터, 점수 생성 자료, SQL 및 Supabase 마이그레이션 파일
- 실행·통합 관련 문서

## 제외
- `.venv_*`, `node_modules`, `frontend/dist` 등 설치/빌드 산출물
- `.env`, 백업 파일, 임시 진단 스크립트 및 캐시

## 테스트 상태
- 백엔드: `USE_MOCK_DB=true`, `SESSION_SECRET` 테스트 값 지정 후 `python -m pytest -q` → 111 passed
- 실제 Supabase 운영 DB는 수정하지 않았습니다. DB 반영은 담당자가 별도로 진행합니다.
- Ollama: 로컬 `qwen2.5:7b` 사용. 외부 Render 실시간 상태 및 전체 브라우저 회귀는 별도 확인이 필요합니다.

## GitHub 업로드
이 폴더에 포함된 `UPLOAD_TO_GITHUB.ps1`을 Windows PowerShell에서 실행하면 저장소 `main`을 직접 clone/pull하고, 이 프로젝트를 `새작업물/통합_추천엔진_Ollama_261126/`에 복사한 뒤 커밋·push합니다. 별도 브랜치나 PR은 만들지 않습니다. Git 인증이 미리 설정되어 있어야 합니다.
