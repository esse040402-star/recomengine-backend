const GUEST_SESSION_IDS_KEY = 'recomengine-guest-session-ids-v1';

export function rememberGuestSession(id) {
  try {
    const current = JSON.parse(localStorage.getItem(GUEST_SESSION_IDS_KEY) || '[]');
    const ids = Array.isArray(current) ? current.filter(value => typeof value === 'string') : [];
    if (!ids.includes(id)) ids.push(id);
    localStorage.setItem(GUEST_SESSION_IDS_KEY, JSON.stringify(ids.slice(-20)));
  } catch (error) {
    console.warn('비회원 진단 세션 ID를 기기에 저장하지 못했습니다.', error);
  }
}

export function getGuestSessionIds() {
  try {
    const value = JSON.parse(localStorage.getItem(GUEST_SESSION_IDS_KEY) || '[]');
    return Array.isArray(value) ? value.filter(id => typeof id === 'string').slice(-20) : [];
  } catch {
    return [];
  }
}

export function clearGuestSessionIds(ids = getGuestSessionIds()) {
  try {
    const remove = new Set(ids);
    const remaining = getGuestSessionIds().filter(id => !remove.has(id));
    if (remaining.length) localStorage.setItem(GUEST_SESSION_IDS_KEY, JSON.stringify(remaining));
    else localStorage.removeItem(GUEST_SESSION_IDS_KEY);
  } catch (error) {
    console.warn('연결된 비회원 진단 세션 목록을 정리하지 못했습니다.', error);
  }
}
