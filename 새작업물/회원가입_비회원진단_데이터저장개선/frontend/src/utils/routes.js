
const pages = new Set([
  'welcome',
  'track-select',
  'home',
  'result',
  'deep-intro',
  'explore',
  'rankings',
  'news',
  'saved',
  'profile',
  'report'
]);

export function resolveRoute(
  route,
  { state, user, forceOnboarding = false, gameExists, firstGame }
) {
  // 비회원도 빠른 진단을 완료하면 전체 기능 이용 가능
  const canEnter = Boolean(state.quick?.completed || user);

  if (!canEnter && !['welcome', 'track-select', 'survey/quick'].includes(route)) {
    return 'welcome';
  }

  if (route === 'welcome' && canEnter && !forceOnboarding) {
    return 'home';
  }

  if (route === 'reviews') {
    return firstGame ? `game/${firstGame}/reviews` : 'home';
  }

  if (route.startsWith('survey/')) {
    const kind = route.slice(7);

    if (!['quick', 'deep', 'preference'].includes(kind)) {
      return canEnter ? 'home' : 'welcome';
    }

    if (!state.drafts?.[kind]) {
      return state[kind]?.completed
        ? (kind === 'quick' ? 'result' : 'report')
        : (canEnter ? 'home' : 'welcome');
    }

    return route;
  }

  if (route.startsWith('game/')) {
    const match = route.match(
      /^game\/([a-z0-9-]+)(?:\/(reviews|requirements))?$/
    );

    return match && gameExists(match[1]) ? route : 'home';
  }

  if (route === 'result' && !state.quick?.completed) {
    return 'home';
  }

  return pages.has(route) ? route : 'home';
}
