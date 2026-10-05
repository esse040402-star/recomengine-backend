import React from 'react';
import { ActionButton, GameImage, Field, FieldArea, Form, Select, Anchor } from '../components/common/Elements.jsx';
export function rankings(ctx) {
  const r = ctx.report();
  r.recommendations = r.recommendations.filter(g => matchesRankCategories(ctx, g));
  return <><div className={"head"}><div><h1>{"게임 랭킹"}</h1><p>{"사람들이 즐기는 게임, 나에게 맞는 순서."}</p></div></div><div className={"tabs"} role={"tablist"} aria-label={"랭킹 기준"}>{React.Children.toArray(['personal', 'global'].map((t, i) => ctx.btn(['내 취향 랭킹', 'Steam 인기 순위'][i], 'rank-tab', 'tab', `role="tab" aria-selected="${ctx.rankTab === t}" data-value="${t}"`)))}</div><>{rankGenreControls(ctx)}{ctx.rankTab === 'personal' ? <><div className={"toolbar"}><span className={"chip"}><>{ctx.icon('Fingerprint')}{r.title}</></span>{ctx.btn('추천 조건 바꾸기', 'filters', 'btn ghost')}</div>{r.recommendations.length ? <><div className={"rank-list"}>{React.Children.toArray(r.recommendations.slice(0, ctx.rankCount).map((g, i) => <article className={"rank-row"} key={i}><span className={"rank-num"}>{String(i + 1).padStart(2, '0')}</span><GameImage src={ctx.gameImage(g.id)} alt={ctx.esc(g.title)} loading={"lazy"} /><div><h3>{ctx.esc(g.title)}</h3><p>{ctx.esc(g.explanation || g.reasons.join(' · '))}</p></div>{ctx.btn(<>{'상세보기'}{ctx.icon('ArrowRight')}</>, 'detail', 'btn ghost', `data-id="${g.id}"`)}</article>))}</div>{r.recommendations.length > ctx.rankCount ? <div className={"load-more"}>{ctx.btn('추천 순위 더 보기', 'rank-more', 'btn')}</div> : ''}</> : ctx.noMatches()}<p className={"fine-context"}>{"설문 응답과 게임 특성으로 정렬한 개인 추천 순위입니다. 전체 이용자의 인기 순위와는 기준이 다릅니다."}</p></> : <>{ctx.marketStamp('rankings')}<div className={"rank-list"}>{React.Children.toArray(filteredGlobalRanks(ctx).map((g, itemIndex) => globalRankRow(ctx, g))) || <div className={"empty"}>{"선택한 기기·장르에 해당하는 게임이 현재 차트에 없습니다."}</div>}</div><div className={"ranking-source"}><p className={"muted"}><>{ctx.rankPlatform === 'all' && ctx.rankGenre === 'all' ? 'Steam 차트 순서' : '수집된 Steam 차트에서 지원 기기·장르로 분류한 결과'}{" · 접속자 수는 조회 시점 기준"}</></p><p className={"muted"}>{"기기는 보유한 게임 지원 정보 기준입니다. 콘솔·모바일을 선택해도 순위와 접속자 수는 Steam 기준이며, 해당 기기의 인기 순위는 아닙니다."}</p>{ctx.link('https://store.steampowered.com/charts/mostplayed', '현재 Steam 순위 보기')}</div></>}</></>;
}
export function globalRankRow(ctx, g) {
  const local = ctx.CATALOG.find(x => x.app === g.app || x.title.toLowerCase() === g.name.toLowerCase());
  return <article className={"rank-row global-row"}><span className={"rank-num"}>{String(g.rank).padStart(2, '0')}</span>{local ? <GameImage src={ctx.gameImage(local.id)} alt={""} loading={"lazy"} /> : <span className={"rank-placeholder"}>{ctx.icon('Trophy')}</span>}<div><h3>{ctx.esc(g.name)}</h3><p>{"동시 접속자"}</p></div><div className={"rank-value"}>{Number.isFinite(g.players) ? g.players.toLocaleString('ko-KR') + '명' : '집계 대기'}</div>{local ? ctx.btn(<>{'게임 상세보기'}{ctx.icon('ArrowRight')}</>, 'detail', 'btn ghost', `data-id="${local.id}"`) : ctx.link(ctx.safeSteamURL(g.url), 'Steam에서 보기', 'btn ghost')}</article>;
}
export function rankGenreControls(ctx) {
  return <section className={"panel ranking-filters"} aria-label={"랭킹 카테고리"}><div className={"ranking-filter-row"}><h2>{"기기"}</h2><div className={"tabs rank-categories"} role={"group"} aria-label={"랭킹 기기"}>{React.Children.toArray([['all', '전체 기기'], ['pc', 'PC'], ['console', '콘솔'], ['mobile', '모바일']].map(([v, t], itemIndex) => ctx.btn(t, 'rank-platform', 'tab', `data-value="${v}" aria-pressed="${ctx.rankPlatform === v}"`)))}</div></div><div className={"ranking-filter-row"}><h2>{"장르"}</h2><div className={"tabs rank-categories"} role={"group"} aria-label={"랭킹 장르"}>{React.Children.toArray(ctx.rankCategories.map(([v, t], itemIndex) => ctx.btn(t, 'rank-genre', 'tab', `data-value="${v}" aria-pressed="${ctx.rankGenre === v}"`)))}</div></div>{ctx.rankPlatform !== 'all' || ctx.rankGenre !== 'all' ? <div className={"ranking-filter-summary"}><span><>{ctx.esc({
            all: '전체 기기',
            pc: 'PC',
            console: '콘솔',
            mobile: '모바일'
          }[ctx.rankPlatform])}{" · "}{ctx.esc(ctx.rankCategories.find(([v]) => v === ctx.rankGenre)?.[1] || '전체')}</></span>{ctx.btn('초기화', 'rank-reset', 'text-btn')}</div> : ''}</section>;
}
export function filteredGlobalRanks(ctx) {
  return ctx.market.rankings.filter(row => matchesRankCategories(ctx, ctx.CATALOG.find(g => g.app === row.app)));
}
// A recommendation session is independent from the saved player profile.

export function matchesRankCategories(ctx, g) {
  return matchesRankGenre(ctx, g, ctx.rankGenre) && matchesRankPlatform(ctx, g);
}
export function matchesRankPlatform(ctx, g) {
  return ctx.rankPlatform === 'all' || !!g?.platforms?.includes(ctx.rankPlatform);
}
export function matchesRankGenre(ctx, g, category) {
  if (category === 'all') return true;
  if (!g) return false;
  const genres = [...(g.genres || []), ...(g.steamGenres || [])].join(' ').toLowerCase();
  if (category === 'fps' && /first.person shooter|1인칭.{0,10}(슈팅|슈터)|\bFPS\b/i.test(ctx.GAME_DETAILS[g.id]?.description || '')) return true;
  if (category === 'fps') return g.camera === 'first' && /슈팅|shooter|fps/.test(genres) || ['cs2', 'apex'].includes(g.id);
  return {
    rpg: /rpg|롤플레잉/,
    action: /액션|action/,
    strategy: /전략|strategy/,
    puzzle: /퍼즐|puzzle/,
    simulation: /시뮬|simulation|경영/,
    casual: /캐주얼|casual|힐링/
  }[category]?.test(genres) || false;
}