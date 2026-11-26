RecomEngine API 문서 테스트 수정

포함 파일:
- app/docs.py: GET /api/survey/questions 한국어 Swagger 설명 추가
- app/routers/survey.py: 해당 엔드포인트에 docs.doc 적용 및 Query 설명 추가
- tests/test_api_docs.py: 실제 OpenAPI 작업 수를 26개로 수정
- tests/test_docs_coverage.py: 라우터 설명 커버리지 기대 개수를 26개로 수정

검증: python -m pytest -q -> 98 passed
프론트: node --test tests/*.test.js -> 8 passed
빌드: npm ci가 패키지 레지스트리 설치 단계에서 5분 제한시간을 초과해 Vite 빌드는 미실행. 소스 빌드 오류로 판정하지 않음.
