import React from 'react';
import { ActionButton, GameImage, Field, FieldArea, Form, Select, Anchor } from '../components/common/Elements.jsx';
export function savedGames(ctx) {
  const items = ctx.state.saved.map(ctx.game).filter(Boolean);
  return <><div className={"head"}><div><h1>{"찜한 게임"}</h1><p>{"다음에 만나고 싶은 세계를 모아두세요."}</p></div></div>{items.length ? <div className={"games-grid"}>{React.Children.toArray(items.map((g, itemIndex) => ctx.card(g, {
        reason: false
      })))}</div> : <div className={"empty"}>{ctx.icon('Bookmark')}<h2>{"마음에 드는 게임을 발견해보세요."}</h2><p>{"게임 카드의 책갈피를 누르면 이곳에 모입니다."}</p>{ctx.routeBtn('추천 게임 보러 가기', 'home', 'btn primary')}</div>}</>;
}