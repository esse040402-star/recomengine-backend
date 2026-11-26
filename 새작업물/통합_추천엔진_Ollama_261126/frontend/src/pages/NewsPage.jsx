import React from 'react';
import { ActionButton, GameImage, Field, FieldArea, Form, Select, Anchor } from '../components/common/Elements.jsx';
export function newsScreen(ctx) {
  let ids = ctx.list().map((g, itemIndex) => g.id);
  if (ctx.newsGame) ids = [ctx.newsGame];
  const items = ctx.market.news.filter(n => ids.includes(n.game)).sort((a, b) => b.date - a.date).slice(0, ctx.newsGame ? 4 : 6);
  const showNews = ['all', 'updates'].includes(ctx.newsTab),
    showNew = ['all', 'new'].includes(ctx.newsTab),
    showSales = ['all', 'sale'].includes(ctx.newsTab);
  return <><div className={"head"}><div><h1>{"게임 뉴스"}</h1><p>{ctx.newsGame ? ctx.esc(ctx.game(ctx.newsGame)?.title) + '의 공식 소식' : '내 취향의 소식부터, 새로운 플레이까지.'}</p></div></div><div className={"toolbar"}><div className={"tabs"} role={"tablist"} aria-label={"소식 종류"}>{React.Children.toArray(['all', 'updates', 'new', 'sale'].map((t, i) => ctx.btn(['전체', '게임 소식', '신작 게임', '할인 게임'][i], 'news-tab', 'tab', `data-value="${t}" role="tab" aria-selected="${ctx.newsTab === t}"`)))}</div>{ctx.newsGame ? ctx.btn('게임 필터 해제', 'news-clear', 'text-btn') : ''}</div><>{ctx.marketStamp('news', ctx.newsGame)}{showNews ? <section className={"news-feed-section"}><div className={"section-head"}><h2>{"내 게임의 공식 소식"}</h2></div><div className={"news-grid"}>{items.length ? React.Children.toArray(items.map((n, itemIndex) => {
            const g = ctx.game(n.game);
            return <article className={"news-card"} key={itemIndex}><GameImage src={ctx.gameImage(g.id)} alt={ctx.esc(g.title)} loading={"lazy"} /><div className={"news-content"}><span className={"chip"}>{ctx.esc(g.title)}</span><h3>{ctx.esc(n.title)}</h3><p><>{new Date(n.date * 1000).toLocaleDateString('ko-KR', {
                      timeZone: 'Asia/Seoul'
                    })}{" · 공식 발표"}</></p><div className={"market-actions"}><>{ctx.link(ctx.safeSteamURL(n.url, `https://store.steampowered.com/news/app/${g.app}`), '소식 읽기', 'btn')}{ctx.btn(<>{'게임 상세보기'}{ctx.icon('ArrowRight')}</>, 'detail', 'text-btn', `data-id="${g.id}"`)}</></div></div></article>;
          })) : <div className={"empty"}><h3>{"현재 조건에서 표시할 소식이 없어요."}</h3><p>{"추천 조건을 바꾸거나 공식 뉴스에서 확인해 보세요."}</p>{ctx.link('https://store.steampowered.com/news/', 'Steam 뉴스 보기')}</div>}</div></section> : ''}{showNew ? <section className={"news-feed-section"}><div className={"section-head"}><h2>{"새로 나온 게임"}</h2>{ctx.link('https://store.steampowered.com/explore/new/', '더 많은 신작', 'text-btn')}</div><div className={"news-grid"}>{React.Children.toArray(ctx.market.newReleases.map((n, itemIndex) => marketCard(ctx, n, 'new')))}</div></section> : ''}{showSales ? <section className={"news-feed-section"}><div className={"section-head"}><h2>{"지금 살펴볼 할인"}</h2>{ctx.link('https://store.steampowered.com/specials/', '전체 할인 보기', 'text-btn')}</div><div className={"news-grid"}>{React.Children.toArray(ctx.market.sales.map((n, itemIndex) => marketCard(ctx, n, 'sale')))}</div></section> : ''}</><p className={"fine-context"}>{"표시된 확인 시점의 Steam 자료입니다. 가격과 할인 종료 여부는 구매 전 상점에서 확인해 주세요."}</p></>;
}
export function marketCard(ctx, item, type) {
  const g = ctx.CATALOG.find(g => g.app === item.app);
  return <article className={"news-card market-card"}>{item.image ? <GameImage src={ctx.esc(ctx.safeSteamImage(item.image))} alt={ctx.esc(item.title)} loading={"lazy"} /> : <div className={"market-art"}>{ctx.icon(type === 'sale' ? 'Bookmark' : 'Gamepad2')}</div>}<div className={"news-content"}><span className={"chip"}>{type === 'sale' ? item.discount ? item.discount + '% 할인' : '할인 탐색' : 'Steam 신작'}</span><h3>{ctx.esc(item.title)}</h3>{type === 'sale' ? <p className={"market-price"}>{item.discount && item.originalPrice ? <del>{ctx.esc(ctx.marketPrice({
            ...item,
            price: item.originalPrice
          }))}</del> : ''}<strong>{ctx.esc(ctx.marketPrice(item))}</strong></p> : ''}<div className={"market-actions"}><>{g ? ctx.btn(<>{'게임 상세보기'}{ctx.icon('ArrowRight')}</>, 'detail', 'btn', `data-id="${g.id}"`) : ctx.link(ctx.safeSteamURL(item.url), 'Steam에서 보기', 'btn')}{g ? ctx.link(ctx.safeSteamURL(item.url), '상점 보기', 'text-btn') : ''}</></div></div></article>;
}