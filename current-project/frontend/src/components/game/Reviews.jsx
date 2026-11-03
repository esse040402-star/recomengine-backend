import React from 'react';
import { ActionButton, GameImage, Field, FieldArea, Form, Select, Anchor } from '../../components/common/Elements.jsx';
export function reviewsScreen(ctx, g) {
  const local = ctx.state.reviews.filter(x => x.game === g.id);
  return <section className={"game-reviews"}><div className={"section-head"}><div><h2>{"유저 평가"}</h2><p>{"실제 평가와 나의 플레이 경험"}</p></div>{ctx.btn(<>{ctx.icon('PenLine')}{'내 평가 작성'}</>, 'write-review', 'btn primary', `data-id="${g.id}"`)}</div><>{steamReviewSummary(ctx, g)}{reviewBrowser(ctx, g.id)}</><div className={"review-toolbar"}><h3>{"내 플레이 기록"}</h3>{ctx.link(`https://store.steampowered.com/app/${g.app}/#app_reviews_hash`, 'Steam 평가 읽기', 'text-btn')}</div>{local.length ? <div className={"review-grid"}>{React.Children.toArray(local.map((x, itemIndex) => <article className={"review"} key={itemIndex}><header><div className={"review-author"}><span className={"review-avatar"}>{ctx.icon('UserRound')}</span><h3>{ctx.esc(x.name)}</h3></div><span className={"rating"} aria-label={"5점 중 " + x.rating + "점"}><>{'★'.repeat(x.rating)}{'☆'.repeat(5 - x.rating)}</></span></header><p>{ctx.esc(x.text)}</p><footer><span>{"내 평가"}</span><span>{"이 브라우저에 저장됨"}</span></footer></article>))}</div> : <div className={"empty compact-empty"}>{ctx.icon('MessagesSquare')}<h3>{"내 플레이 경험을 남겨보세요."}</h3><p>{"직접 작성한 평가는 이 브라우저에 저장됩니다."}</p></div>}</section>;
}
export function steamReviewSummary(ctx, g) {
  const r = ctx.market.reviews[g.id];
  if (!r?.total) return <><div className={"note"}>{r ? '아직 등록된 Steam 평가가 없어요.' : 'Steam 평가 집계를 아직 가져오지 못했어요.'}</div>{marketStamp(ctx, 'reviews', g.id)}</>;
  const positive = Math.round(r.positive / r.total * 100),
    labels = {
      'Overwhelmingly Positive': '압도적으로 긍정적',
      'Very Positive': '매우 긍정적',
      'Mostly Positive': '대체로 긍정적',
      'Positive': '긍정적',
      'Mixed': '복합적',
      'Mostly Negative': '대체로 부정적',
      'Very Negative': '매우 부정적',
      'Overwhelmingly Negative': '압도적으로 부정적',
      'Negative': '부정적'
    };
  return <><div className={"steam-review-summary"}><div><span className={"chip"}>{"Steam 실제 평가 · 전체 언어"}</span><h3>{ctx.esc(labels[r.description] || r.description)}</h3><p><>{Number(r.total).toLocaleString('ko-KR')}{"개 평가 중 긍정 평가 "}{positive}{"%"}</></p></div><div className={"review-meter"} role={"img"} aria-label={"긍정 평가 " + positive + "%"}><strong>{positive}<span>{"%"}</span></strong><div><i style={ctx.style("width:" + positive + "%")} /></div></div></div>{marketStamp(ctx, 'reviews', g.id)}</>;
}
export function reviewBrowser(ctx, id) {
  const p = ctx.reviewPanel(id),
    f = p.filters,
    rows = filteredReviews(ctx, id),
    snapshot = ctx.window.STEAM_REVIEWS?.games[id],
    allCount = p.live?.length ?? snapshot?.items.length ?? 0;
  return <section className={"steam-review-browser"} data-review-game={id}><div className={"section-head"}><div><h3>{"Steam 플레이어 리뷰"}</h3><p className={"review-scope"}><>{p.live ? 'Steam 조회 결과' : '저장된 리뷰 ' + allCount + '개'}{" · 조건에 맞는 "}{rows.length}{"개"}</></p></div>{ctx.marketOnline ? ctx.btn(<>{ctx.icon('RotateCcw')}{'리뷰 새로 불러오기'}</>, 'steam-reviews-refresh', 'text-btn', `data-id="${id}" ${p.busy ? 'disabled' : ''}`) : ''}</div><div className={"review-filters"}><>{ctx.selectField('평가', 'sentiment', f.sentiment, [['all', '전체'], ['positive', '추천'], ['negative', '비추천']], 'review')}{ctx.selectField('작성 기간', 'days', f.days, [['all', '전체 기간'], ['30', '최근 30일'], ['180', '최근 6개월'], ['365', '최근 1년']], 'review')}{ctx.selectField('리뷰 언어', 'language', f.language, [['all', '모든 언어'], ['koreana', '한국어'], ['english', '영어']], 'review')}{ctx.selectField('정렬', 'sort', f.sort, [['recent', '최신순'], ['helpful', '도움순']], 'review')}</></div><div className={"review-live-status"} role={"status"}>{p.busy ? <><span className={"spinner"} />{" Steam에서 리뷰를 불러오고 있어요."}</> : p.error ? ctx.esc(p.error) : `${ctx.esc(ctx.marketDate(p.checkedAt || snapshot?.checkedAt))} 확인 · 표시한 리뷰의 발췌입니다.`}</div><>{rows.length ? <div className={"steam-review-grid"}>{React.Children.toArray(rows.slice(0, p.count).map((row, itemIndex) => steamReviewCard(ctx, row)))}</div> : <div className={"empty compact-empty"}><h3>{p.busy ? '조건에 맞는 리뷰를 찾고 있어요.' : '현재 불러온 리뷰에는 일치하는 평가가 없어요.'}</h3><p>{ctx.marketOnline ? '조건을 바꾸거나 Steam에서 다시 불러와 보세요.' : '저장된 리뷰에서 필터링합니다. 서버로 실행하면 Steam 리뷰를 추가로 조회할 수 있어요.'}</p></div>}{rows.length > p.count || p.cursor ? <div className={"load-more"}>{ctx.btn(p.busy ? '불러오는 중' : '리뷰 더 보기', 'steam-reviews-more', 'btn', `data-id="${id}" ${p.busy ? 'disabled' : ''}`)}</div> : ''}</><p className={"fine-context"}>{"추천 비율은 전체 언어의 Steam 집계입니다. 위 필터는 리뷰 목록에만 적용됩니다. 도움순은 불러온 결과 안에서 정렬하며 기간은 작성일 기준입니다."}</p></section>;
}
export function filteredReviews(ctx, id) {
  const p = ctx.reviewPanel(id),
    f = p.filters,
    items = p.live || ctx.window.STEAM_REVIEWS?.games[id]?.items || [],
    cutoff = f.days === 'all' ? 0 : Date.now() / 1000 - Number(f.days) * 86400;
  return items.filter(r => (f.sentiment === 'all' || r.positive === (f.sentiment === 'positive')) && (f.language === 'all' || r.language === f.language) && r.created >= cutoff).sort((a, b) => f.sort === 'helpful' ? b.helpful - a.helpful || b.created - a.created : b.created - a.created);
}
export function steamReviewCard(ctx, r) {
  return <article className={"steam-review-card"}><header><span className={"review-verdict " + (r.positive ? 'positive' : 'negative')}><>{ctx.icon('ThumbsUp')}{r.positive ? '추천' : '비추천'}</></span><time dateTime={new Date(r.created * 1000).toISOString()}>{new Date(r.created * 1000).toLocaleDateString('ko-KR')}</time></header><blockquote><>{ctx.esc(r.text || '(텍스트 없는 평가)')}{r.truncated ? '…' : ''}</></blockquote><div className={"review-facts"}><span><>{"플레이 "}{Number(r.hours).toLocaleString('ko-KR')}{"시간"}</></span><span><>{"도움 됨 "}{Number(r.helpful).toLocaleString('ko-KR')}</></span>{r.receivedFree ? <span>{"무료 제공받음"}</span> : r.purchased ? <span>{"Steam 구매"}</span> : ''}</div>{ctx.link(ctx.safeSteamURL(r.url), 'Steam 원문 보기', 'text-btn')}</article>;
}
export function marketStamp(ctx, section, id) {
  const busy = ctx.marketBusy === section;
  return <div className={"market-status"}><span><>{ctx.icon('Radio')}{" "}{ctx.esc(ctx.marketDate(section === 'reviews' ? ctx.marketDates.reviews[id] : section === 'news' && id ? ctx.newsDatesByGame[id] || ctx.marketDates.news : ctx.marketDates[section]))}{" 확인"}</></span>{ctx.marketOnline ? ctx.btn(<>{busy ? <span className={"spinner"} /> : ctx.icon('RotateCcw')}{busy ? '불러오는 중' : '새로 불러오기'}</>, 'refresh-market', 'text-btn', `data-value="${section}" ${id ? `data-id="${id}"` : ''} ${busy ? 'disabled aria-busy="true"' : ''}`) : ''}</div>;
}