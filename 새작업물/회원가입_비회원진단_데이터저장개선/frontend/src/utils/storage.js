import { initialState } from '../state/appReducer';
import E from '../services/preferenceEngine';

export const STORAGE_KEY = 'recom-integrated-v3';

// 게스트 데이터 보관 기간: 7일
const GUEST_TTL = 7 * 24 * 60 * 60 * 1000;

export function normalizeState(value) {
  const s = {
    ...structuredClone(initialState),
    ...value,
    profile: {
      ...initialState.profile,
      ...value?.profile,
    },
    home: {
      ...initialState.home,
      ...value?.home,
    },
    drafts: value?.drafts || {},
  };

  if (s.quick?.completed && !s.quick.questions) {
    s.quick.questions = E.legacyQuickQuestions(s.track);
  }

  for (const p of [s.preference, s.drafts.preference]) {
    if (p && s.track) {
      p.track = p.track || s.track;
      p.questions = p.questions || E.profileQuestions(p.track);
    }
  }

  if (s.drafts.quick && !s.drafts.quick.schema) {
    delete s.drafts.quick;
  }

  return s;
}

// 게스트 데이터 불러오기: 7일이 지나면 자동 삭제
export function readState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);

    if (!raw) {
      return structuredClone(initialState);
    }

    const saved = JSON.parse(raw);

    // 저장 시각이나 데이터가 없는 오래된 형식은 사용하지 않음
    if (
      !saved ||
      typeof saved.savedAt !== 'number' ||
      !saved.state
    ) {
      localStorage.removeItem(STORAGE_KEY);
      return structuredClone(initialState);
    }

    // 마지막 저장 이후 7일이 지났으면 만료
    if (Date.now() - saved.savedAt >= GUEST_TTL) {
      localStorage.removeItem(STORAGE_KEY);
      return structuredClone(initialState);
    }

    return normalizeState(saved.state);
  } catch {
    return structuredClone(initialState);
  }
}

// 게스트 데이터 임시 저장
export function writeGuestState(state) {
  try {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        savedAt: Date.now(),
        state,
      })
    );

    return true;
  } catch {
    return false;
  }
}

// 로그인 사용자의 계정별 저장 및 복구용 저장
export function writeState(state, key = STORAGE_KEY) {
  try {
    localStorage.setItem(key, JSON.stringify(state));
    return true;
  } catch {
    return false;
  }
}
