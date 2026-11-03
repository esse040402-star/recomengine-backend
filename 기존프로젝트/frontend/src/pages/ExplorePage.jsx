import React from 'react';
import { ActionButton, GameImage, Field, FieldArea, Form, Select, Anchor } from '../components/common/Elements.jsx';
export function exploreScreen(ctx) {
  const s = ctx.exploreState,
    genres = [...new Set(ctx.CATALOG.flatMap(g => ctx.GAME_DETAILS[g.id]?.genres || []))].sort();
  return <><div className={"head"}><div><span className={"chip"}><>{"Steam · "}{ctx.CATALOG.length}{"개 게임"}</></span><h1 className={"explore-title"}>{"새로운 플레이를 찾아보세요."}</h1><p>{"내 취향에서 시작해, 더 넓은 게임 세계로."}</p></div></div><div className={"explore-search"}>{ctx.icon('Search')}<Field id={"explore-search"} type={"search"} placeholder={"게임 이름, 장르, 개발사 검색"} aria-label={"Steam 게임 검색"} value={ctx.esc(s.query)} /></div><div className={"explore-filters"}><>{ctx.selectField('장르', 'genre', s.genre, [['all', '모든 장르'], ...genres.map((x, itemIndex) => [x, x])])}{ctx.selectField('가격', 'price', s.price, [['all', '전체 가격'], ['free', '무료'], ['sale', '할인 중'], ['under20', '2만 원 이하']])}{ctx.selectField('유저 평가', 'rating', s.rating, [['all', '모든 평가'], ['80', '80% 이상 긍정'], ['90', '90% 이상 긍정']])}{ctx.selectField('언어', 'language', s.language, [['all', '모든 언어'], ['korean', '한국어 지원']])}{ctx.selectField('정렬', 'sort', s.sort, [['match', '내 취향순'], ['positive', '긍정 비율순'], ['reviews', '평가 많은 순'], ['price', '낮은 가격순'], ['name', '이름순']])}</></div><div id={"explore-results"}>{exploreResults(ctx)}</div><p className={"fine-context"}>{"가져온 Steam 카탈로그 안에서 검색합니다. 가격·지원 언어·평가는 각 게임의 확인 시점 기준이며 구매 전 상점에서 확인해 주세요."}</p></>;
}
export function exploreResults(ctx) {
  const rows = exploreGames(ctx);
  return <><div className={"explore-result-head"}><span><strong>{rows.length}</strong>{"개 게임"}</span><span className={"muted"}>{"Steam PC 버전 기준"}</span></div>{rows.length ? <><div className={"games-grid explore-grid"}>{React.Children.toArray(rows.slice(0, ctx.exploreState.count).map((g, itemIndex) => ctx.card(g, {
          reason: false
        })))}</div>{rows.length > ctx.exploreState.count ? <div className={"load-more"}>{ctx.btn('게임 더 보기', 'explore-more', 'btn')}</div> : ''}</> : <div className={"empty"}>{ctx.icon('SearchX')}<h3>{"조건에 맞는 게임이 없어요."}</h3>{ctx.btn('조건 초기화', 'explore-reset', 'btn')}</div>}</>;
}
export function exploreGames(ctx) {
  const s = ctx.exploreState,
    scores = new Map(ctx.list().map((g, i) => [g.id, i])),
    q = s.query.trim().toLocaleLowerCase();
  let rows = ctx.CATALOG.filter(g => {
    const d = ctx.GAME_DETAILS[g.id] || {},
      score = ctx.steamScore(g.id);
    return (!q || [g.title, g.name, ...(d.genres || []), ...(d.developers || [])].join(' ').toLocaleLowerCase().includes(q)) && (s.genre === 'all' || d.genres?.includes(s.genre)) && (s.price === 'all' || s.price === 'free' && d.price?.price === 0 || s.price === 'sale' && d.price?.discount > 0 || s.price === 'under20' && d.price?.currency === 'KRW' && d.price.price <= 2000000) && (s.rating === 'all' || score !== null && score >= Number(s.rating)) && (s.language === 'all' || d.korean);
  });
  rows.sort((a, b) => s.sort === 'positive' ? (ctx.steamScore(b.id) ?? -1) - (ctx.steamScore(a.id) ?? -1) || (ctx.market.reviews[b.id]?.total || 0) - (ctx.market.reviews[a.id]?.total || 0) : s.sort === 'reviews' ? (ctx.market.reviews[b.id]?.total || 0) - (ctx.market.reviews[a.id]?.total || 0) : s.sort === 'price' ? ctx.steamKRW(a.id) - ctx.steamKRW(b.id) : s.sort === 'name' ? a.title.localeCompare(b.title) : (scores.get(a.id) ?? 9999) - (scores.get(b.id) ?? 9999));
  return rows;
}