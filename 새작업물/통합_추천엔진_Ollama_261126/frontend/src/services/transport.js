// 현재 서버의 /api 경로를 유지합니다. v1 경로로의 전환은 서버 배포와 함께 해야 합니다.
export const apiBase = (import.meta.env?.VITE_API_BASE_URL || '').replace(/\/$/, '');
export const apiEnabled = import.meta.env?.VITE_API_ENABLED !== 'false';
export class ApiError extends Error {
  constructor(message, status = 0, code = 'REQUEST_FAILED', details = []) {
    super(message); this.name = 'ApiError'; this.status = status; this.code = code; this.details = details;
  }
}
export async function request(path, {method = 'GET', body, timeout = 12000, signal, base = apiBase} = {}) {
  if (!path.startsWith('/api/')) throw new ApiError('올바르지 않은 API 경로입니다.');
  const controller = new AbortController();
  const abort = () => controller.abort(signal?.reason);
  if (signal?.aborted) abort(); else signal?.addEventListener('abort', abort, {once:true});
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(base.replace(/\/$/, '') + path, {
      method, credentials: 'include', signal: controller.signal,
      headers: {Accept:'application/json', ...(body !== undefined ? {'Content-Type':'application/json'} : {})},
      ...(body !== undefined ? {body:JSON.stringify(body)} : {}),
    });
    if (response.status === 204) return null;
    const raw = await response.text();
    let data;
    try { data = raw ? JSON.parse(raw) : null; }
    catch { throw new ApiError('서버 응답을 읽지 못했습니다. API 연결 주소를 확인해주세요.', response.status, 'INVALID_RESPONSE'); }
    if (!response.ok) throw new ApiError(
      (typeof data?.message === 'string' && data.message) || (typeof data?.error === 'string' && data.error) || '요청에 실패했습니다.',
      response.status, data?.code || 'REQUEST_FAILED', data?.details || data?.detail || []);
    return data;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (signal?.aborted) throw error;
    if (controller.signal.aborted) throw new ApiError('응답 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.', 0, 'TIMEOUT');
    throw new ApiError('서버에 연결하지 못했습니다. 연결 상태를 확인해주세요.', 0, 'NETWORK_ERROR');
  } finally { clearTimeout(timer); signal?.removeEventListener('abort', abort); }
}
