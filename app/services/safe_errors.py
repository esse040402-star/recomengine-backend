"""외부 API 오류를 로그/응답에 남길 때 API 키가 새지 않게 한다.
httpx 오류 메시지에는 요청 주소 전체가 들어 있는데, RAWG·스팀은 키를 주소(?key=...)에 넣는다."""


def describe(exc: BaseException) -> str:
    """'HTTPStatusError(status=401)' 처럼 종류와 상태 코드만."""
    response = getattr(exc, "response", None)
    code = getattr(response, "status_code", None)
    return f"{type(exc).__name__}(status={code})" if code else type(exc).__name__


def status_hint(exc: BaseException) -> str:
    """사용자에게 보여줄 짧은 한국어 설명."""
    code = getattr(getattr(exc, "response", None), "status_code", None)
    if code in (401, 403):
        return f"API 키가 올바르지 않거나 권한이 없습니다 (상태 코드 {code}). .env 의 키를 확인하세요."
    if code == 429:
        return "외부 API 사용 한도를 넘었습니다 (상태 코드 429). 잠시 후 다시 시도하세요."
    if code:
        return f"외부 API가 오류를 돌려줬습니다 (상태 코드 {code})."
    return "외부 API에 연결하지 못했습니다. 인터넷 연결을 확인하세요."
