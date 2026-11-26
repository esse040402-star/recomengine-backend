import React from 'react';
import { ActionButton, GameImage, Field, FieldArea, Form, Select, Anchor } from '../../components/common/Elements.jsx';
export function card(ctx, g, {
  reason = true
} = {}) {
  const isSaved = ctx.state.saved.includes(g.id);
  return <article key={g.id} className={"game-card"} data-game-id={g.id}><>{ctx.btn(<GameImage src={ctx.gameImage(g.id)} alt={ctx.esc(g.title) + " 게임 이미지"} loading={"lazy"} />, 'detail', 'game-art-button', `data-id="${g.id}" aria-label="${ctx.esc(g.title)} 상세보기"`)}{ctx.btn(ctx.icon(isSaved ? 'BookmarkCheck' : 'Bookmark'), 'save', 'icon-btn save', `data-id="${g.id}" aria-label="${ctx.esc(g.title)} ${isSaved ? '찜 해제' : '찜하기'}" aria-pressed="${isSaved}"`)}</><div className={"game-info"}><h3>{ctx.esc(g.title)}</h3><p>{ctx.esc(reason && g.reasons ? g.explanation || g.reasons.slice(0, 2).join(' · ') : g.genres.slice(0, 2).join(' · '))}</p>{steamBadge(ctx, g)}<div className={"game-card-actions"}>{ctx.btn(<>{'게임 상세보기'}{ctx.icon('ArrowRight')}</>, 'detail', 'text-btn', `data-id="${g.id}"`)}</div></div></article>;
}
export function steamBadge(ctx, g) {
  const score = ctx.steamScore(g.id),
    d = ctx.GAME_DETAILS[g.id];
  return <div className={"steam-card-meta"}><span className={"steam-positive"}>{score === null ? '평가 집계 없음' : <><><>{ctx.icon('ThumbsUp')}{' '}</>{score}</>{'% 긍정'}</>}</span><span>{d?.price ? ctx.esc(ctx.marketPrice(d.price)) : '가격 확인'}</span></div>;
}
export function noMatches(ctx) {
  return <div className={"empty"}>{ctx.icon('SearchX')}<h2>{"지금 조건에 맞는 게임이 없어요."}</h2><p><>{"준비된 "}{ctx.CATALOG.length}{"개 게임 중 모든 조건을 만족한다고 확인된 후보가 없습니다."}{ctx.report().prefs.lowSpec ? ' 저사양 지원을 확인할 자료가 부족합니다.' : ''}{ctx.report().prefs.avoid.includes('monetization') ? ' 과금·광고 유무가 미확인인 게임은 제외했습니다.' : ''}{" 추천 조건을 조정하거나 다른 기기로 다시 답해보세요."}</></p>{ctx.btn('추천 조건 바꾸기', 'filters', 'btn primary')}</div>;
}