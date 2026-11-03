const pages=new Set(['welcome','home','result','deep-intro','explore','rankings','news','saved','profile','report']);
export function resolveRoute(route,{state,user,forceOnboarding=false,gameExists,firstGame}) {
  const canEnter=!!(state.quick?.completed||user);
  if(!canEnter&&route!=='welcome'&&route!=='survey/quick')return 'welcome';
  if(route==='welcome'&&canEnter&&!forceOnboarding)return 'home';
  if(route==='reviews')return firstGame?`game/${firstGame}/reviews`:'home';
  if(route.startsWith('survey/')) {
    const kind=route.slice(7);
    if(!['quick','deep','preference'].includes(kind))return canEnter?'home':'welcome';
    if(!state.drafts[kind])return state[kind]?.completed?(kind==='quick'?'result':'report'):(canEnter?'home':'welcome');
    return route;
  }
  if(route.startsWith('game/')) {
    const match=route.match(/^game\/([a-z0-9-]+)(?:\/(reviews|requirements))?$/);
    return match&&gameExists(match[1])?route:'home';
  }
  if(route==='result'&&!state.quick?.completed)return 'home';
  return pages.has(route)?route:'home';
}
