import React from 'react';
import { ActionButton, GameImage, Field, FieldArea, Form, Select, Anchor } from '../components/common/Elements.jsx';
export function gamePage(ctx) {
  const current = ctx.gameRoute(),
    g = ctx.game(current.id),
    d = ctx.GAME_DETAILS[g.id] || {},
    copy = ctx.GAME_COPY[g.id];
  return <article className={"game-page"} data-game={g.id}><div className={"game-back-row"}>{ctx.btn(<>{ctx.icon('ChevronLeft')}{'돌아가기'}</>, 'game-back', 'text-btn')}<span className={"game-breadcrumb"}>{"게임 둘러보기 "}<span>{"/"}</span><>{" "}{ctx.esc(g.title)}</></span></div><header className={"game-page-heading"}><div className={"chips"}>{React.Children.toArray(g.genres.map((x, itemIndex) => <span className={"chip"} key={itemIndex}>{ctx.esc(x)}</span>))}</div><h1>{ctx.esc(g.title)}</h1><p>{ctx.esc(g.line)}</p><div className={"detail-shortcuts"}><>{ctx.btn(<>{ctx.icon('Fingerprint')}{'추천에 의견 남기기'}</>, 'game-feedback', 'btn', `data-id="${g.id}"`)}{ctx.btn(<>{ctx.icon('MessagesSquare')}{'유저 평가 보기'}</>, 'game-tab', 'btn ghost', `data-id="${g.id}" data-value="reviews"`)}{ctx.btn(<>{ctx.icon('SlidersHorizontal')}{'시스템 사양'}</>, 'game-tab', 'text-btn', `data-id="${g.id}" data-value="requirements"`)}</></div></header><div className={"game-detail-grid"}>{gameGallery(ctx, g)}<aside className={"game-summary"}><GameImage className={"game-summary-cover"} src={ctx.gameImage(g.id)} alt={ctx.esc(g.title) + " 대표 이미지"} /><div className={"game-summary-body"}>{steamInfo(ctx, g)}<div className={"game-fit"}><span><>{ctx.icon('Fingerprint')}{"내 취향과의 연결"}</></span><p>{ctx.esc(gameFit(ctx, g))}</p>{gameEvidence(ctx, g)}</div><dl className={"game-facts"}><div><dt>{"개발사"}</dt><dd>{ctx.esc((d.developers || []).join(', ') || '공식 상점에서 확인')}</dd></div><div><dt>{"출시일"}</dt><dd>{ctx.esc(d.releaseDate || '공식 상점에서 확인')}</dd></div><div><dt>{"플레이"}</dt><dd>{g.social.map((x, itemIndex) => ({
                  solo: '싱글 플레이',
                  coop: '협동',
                  pvp: '온라인 대전'
                })[x]).join(' · ')}</dd></div><div><dt>{"지원 기기"}</dt><dd>{"Steam PC 버전"}</dd></div></dl>{ctx.link(d.source || `https://store.steampowered.com/app/${g.app}/`, 'Steam에서 게임 보기', 'btn primary game-store')}<div className={"game-summary-actions"}><>{ctx.btn(<>{ctx.icon(ctx.state.saved.includes(g.id) ? 'BookmarkCheck' : 'Bookmark')}{ctx.state.saved.includes(g.id) ? '찜한 게임' : '찜하기'}</>, 'save', 'btn', `data-id="${g.id}" aria-pressed="${ctx.state.saved.includes(g.id)}"`)}{ctx.btn(<>{ctx.icon('Waves')}{'이 게임 색상 적용'}</>, 'apply-theme', 'btn ghost', `data-id="${g.id}"`)}</></div></div></aside></div><div className={"game-section"} id={"game-section"}><div className={"game-tabs"} role={"tablist"} aria-label={"게임 상세 정보"}>{React.Children.toArray([['overview', '게임 소개', 'Gamepad2'], ['reviews', '유저 평가', 'MessagesSquare'], ['requirements', '시스템 사양', 'SlidersHorizontal']].map(([tab, label, i], itemIndex) => ctx.btn(<>{ctx.icon(i)}{label}</>, 'game-tab', 'game-tab', `id="game-tab-${tab}" role="tab" aria-controls="game-tab-content" aria-selected="${current.tab === tab}" tabindex="${current.tab === tab ? '0' : '-1'}" data-value="${tab}" data-id="${g.id}"`)))}</div><div id={"game-tab-content"} role={"tabpanel"} aria-labelledby={"game-tab-" + current.tab} tabIndex={"0"}>{gameSection(ctx, g, current.tab)}</div></div><footer className={"game-source"}><>{"게임 정보·이미지: "}{ctx.link(d.source || `https://store.steampowered.com/app/${g.app}/`, 'Steam 공식 상점', 'source-link')}</><span><>{ctx.esc(ctx.marketDate(d.checkedAt || '2026-09-29'))}{" 확인"}</></span></footer></article>;
}
export function gameSection(ctx, g, tab) {
  if (tab === 'reviews') return gameReviews(ctx, g);
  if (tab === 'requirements') return gameRequirements(ctx, g);
  return steamOverview(ctx, g);
}
export function gameRequirements(ctx, g) {
  const d = ctx.GAME_DETAILS[g.id] || {};
  return <section className={"game-requirements"}><div className={"section-head"}><div><h2>{"PC 시스템 사양"}</h2><p>{"Steam에 안내된 PC 버전 기준입니다."}</p></div></div><div className={"requirements-grid"}>{React.Children.toArray([['minimum', '최소 사양'], ['recommended', '권장 사양']].map(([key, label], itemIndex) => <article className={"requirements-card"} key={itemIndex}><h3>{label}</h3>{d[key]?.length ? <dl>{React.Children.toArray(d[key].map(([label, value], itemIndex) => <div key={itemIndex}><dt>{ctx.esc(label)}</dt><dd>{ctx.esc(value)}</dd></div>))}</dl> : <p>{"별도의 사양이 안내되지 않았습니다. 공식 상점에서 확인해 주세요."}</p>}</article>))}</div><p className={"game-data-note"}>{"업데이트에 따라 사양과 지원 환경이 달라질 수 있습니다. 구매 전 공식 안내를 확인해 주세요."}</p></section>;
}
export function gameReviews(ctx, g) {
  return ctx.reviewsScreen(g);
}
export function gameGallery(ctx, g) {
  const images = gameMedia(ctx, g.id),
    index = Math.min(ctx.galleryPositions.get(g.id) || 0, images.length - 1);
  return <section className={"game-gallery"} aria-label={ctx.esc(g.title) + " 이미지 갤러리"} data-gallery={g.id}><div className={"gallery-view"}><GameImage id={"gallery-image"} src={ctx.esc(images[index].src)} alt={ctx.esc(images[index].alt)} /><>{ctx.btn(ctx.icon('ChevronLeft'), 'gallery-prev', 'icon-btn gallery-arrow previous', 'aria-label="이전 게임 이미지"')}{ctx.btn(ctx.icon('ChevronRight'), 'gallery-next', 'icon-btn gallery-arrow next', 'aria-label="다음 게임 이미지"')}</><span className={"gallery-count"} aria-live={"polite"}><>{index + 1}{" / "}{images.length}</></span></div><div className={"gallery-thumbs"}>{React.Children.toArray(images.map((image, i) => ctx.btn(<GameImage src={ctx.esc(image.thumb || image.src)} alt={""} loading={"lazy"} />, 'gallery-select', 'gallery-thumb', `data-value="${i}" aria-label="${ctx.esc(image.alt)} 보기" aria-pressed="${index === i}"`)))}</div></section>;
}
export function gameMedia(ctx, id) {
  return [...(ctx.GAME_DETAILS[id]?.screenshots || []).map((x, i) => ({
    ...x,
    src: ctx.steamMediaURL(id, 'screenshot', i, x.src),
    thumb: ctx.steamMediaURL(id, 'thumb', i, x.thumb || x.src)
  })), {
    src: ctx.gameImage(id, 'hero'),
    thumb: ctx.gameImage(id),
    alt: ctx.game(id).title + ' 대표 아트'
  }];
}
export function gameFit(ctx, g) {
  const r = ctx.report(),
    rec = r.recommendations.find(x => x.id === g.id),
    excluded = r.prefs.avoid.filter(a => g.risks.includes(a)),
    platformOK = !r.prefs.platforms.length || r.prefs.platforms.some(p => g.platforms.includes(p));
  return excluded.length ? `${excluded.map((x, itemIndex) => ctx.E.RISK_LABELS[x]).join(', ')} 조건으로 현재 추천에서 제외되어 있어요.` : !platformOK ? '현재 고른 기기 조건과는 맞지 않아요.' : rec ? rec.explanation : '이 게임의 특징과 내 취향을 함께 살펴보세요.';
}
export function gameEvidence(ctx, g) {
  const rec = ctx.report().recommendations.find(x => x.id === g.id);
  if (!rec?.matches?.length) return '';
  return <details className={"fit-evidence"} ref={ctx.detailsRef}><summary><>{"추천 근거 보기"}{ctx.icon('ChevronRight')}</></summary><div>{React.Children.toArray(rec.matches.map((m, itemIndex) => <section key={itemIndex}><strong>{ctx.esc(m.label)}</strong><p>{ctx.esc(m.detail)}</p>{m.answer ? <blockquote><>{"내 답변 · "}{ctx.esc(m.answer)}</></blockquote> : ''}</section>))}</div></details>;
}
export function steamOverview(ctx, g) {
  const d = ctx.GAME_DETAILS[g.id] || {},
    similar = ctx.list().filter(x => x.id !== g.id && (ctx.GAME_DETAILS[x.id]?.genres || []).some(t => (d.genres || []).includes(t))).slice(0, 3);
  return <section className={"game-overview"}><div className={"game-about"}><div><span className={"section-eyebrow"}>{"Steam 상점 소개"}</span><h2>{ctx.esc(g.title)}</h2></div><p>{ctx.esc(d.description || g.line)}</p></div><div className={"steam-feature-grid"}><article><h3>{"장르"}</h3><div className={"chips"}>{React.Children.toArray((d.genres || g.genres).map((x, itemIndex) => <span className={"chip"} key={itemIndex}>{ctx.esc(x)}</span>))}</div></article><article><h3>{"플레이 기능"}</h3><p>{ctx.esc((d.categories || []).slice(0, 8).map((x, itemIndex) => x.label).join(' · ') || '상점에서 확인해주세요.')}</p></article><article><h3>{"지원 정보"}</h3><p><>{d.controller === 'full' ? '컨트롤러 완전 지원' : d.controller === 'partial' ? '컨트롤러 일부 지원' : '컨트롤러 지원 표기 없음'}{d.achievements !== null && d.achievements !== undefined ? ' · 도전 과제 ' + d.achievements + '개' : ''}</></p></article></div><div className={"game-before-play"}><div>{ctx.icon('Fingerprint')}<h3>{"추천 기준 안내"}</h3></div><p>{g.classification === 'steam-derived' ? '추가된 게임의 취향은 Steam 장르·플레이 방식으로 추정했습니다. 시점·난이도·멀미 등 미확인 요소가 있어, 불호 조건이 엄격하면 추천 후보에서 제외될 수 있습니다.' : ctx.esc(g.note)}</p></div><div className={"game-next-links"}><>{ctx.btn(<><span>{ctx.icon('MessagesSquare')}<strong>{"Steam 리뷰 살펴보기"}</strong></span>{ctx.icon('ArrowRight')}</>, 'game-tab', 'game-next-link', `data-id="${g.id}" data-value="reviews"`)}{ctx.btn(<><span>{ctx.icon('Newspaper')}<strong>{"이 게임의 공식 소식"}</strong></span>{ctx.icon('ArrowRight')}</>, 'game-news', 'game-next-link', `data-id="${g.id}"`)}</></div>{similar.length ? <section className={"section"}><div className={"section-head"}><h2>{"이어서 만나볼 게임"}</h2>{ctx.routeBtn('전체 게임 탐색', 'explore', 'text-btn')}</div><div className={"games-grid"}>{React.Children.toArray(similar.map((x, itemIndex) => ctx.card(x)))}</div></section> : ''}</section>;
}
export function steamInfo(ctx, g) {
  const d = ctx.GAME_DETAILS[g.id] || {},
    score = ctx.steamScore(g.id);
  return <div className={"steam-detail-info"}><span className={"chip"}>{"Steam 공식 정보"}</span><div className={"steam-price-row"}><strong>{d.price ? ctx.esc(ctx.marketPrice(d.price)) : '상점에서 가격 확인'}</strong>{d.price?.discount ? <><span className={"discount-badge"}><>{"−"}{d.price.discount}{"%"}</></span><del>{ctx.esc(ctx.marketPrice({
            ...d.price,
            price: d.price.originalPrice
          }))}</del></> : ''}</div><div className={"steam-detail-facts"}><span>{score === null ? '평가 집계 없음' : score + '% 긍정 · ' + Number(ctx.market.reviews[g.id]?.total).toLocaleString('ko-KR') + '개 평가'}</span><span>{d.korean ? '한국어 지원' : '한국어 지원 표기 없음'}</span><span>{Object.entries(d.os || {}).filter(([, v]) => v).map(([k], itemIndex) => ({
          windows: 'Windows',
          mac: 'macOS',
          linux: 'Linux'
        })[k]).join(' · ') || 'PC'}</span></div>{ctx.marketOnline ? ctx.btn(<>{ctx.icon('RotateCcw')}{'가격·정보 갱신'}</>, 'steam-details-refresh', 'text-btn', `data-id="${g.id}"`) : ''}</div>;
}