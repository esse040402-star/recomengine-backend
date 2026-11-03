import { useState, useRef, useEffect } from 'react';
import { useView } from '../../state/ViewContext';
export default function HeroCarousel({
  items
}) {
  const c = useView(),
    [index, setIndex] = useState(0),
    stage = useRef(null),
    touch = useRef(null);
  const game = items[index % items.length];
  useEffect(() => {
    if (c.state.home.style === 'follow') document.documentElement.dataset.gameTheme = game.id;
  }, [game.id, c.state.home.style]);
  const move = dir => {
    setIndex(i => (i + dir + items.length) % items.length);
    if (!matchMedia('(prefers-reduced-motion: reduce)').matches) stage.current?.animate([{
      opacity: .1,
      transform: `translateX(${dir * 50}px)`
    }, {
      opacity: 1,
      transform: 'translateX(0)'
    }], {
      duration: 560,
      easing: 'cubic-bezier(.16,1,.3,1)'
    });
  };
  return <section className="hero-carousel" aria-roledescription="카루셀" aria-label="맞춤 추천 게임"><div className="hero-stage" ref={stage} onTouchStart={e => touch.current = e.touches[0].clientX} onTouchEnd={e => {
      const dx = e.changedTouches[0].clientX - touch.current;
      if (Math.abs(dx) > 50) move(dx < 0 ? 1 : -1);
    }}>{c.heroSlide(game)}</div><div className="hero-controls"><button className="icon-btn" aria-label="이전 추천 게임" onClick={() => move(-1)}>{c.icon('ChevronLeft')}</button><span className="hero-counter">{index % items.length + 1} / {items.length}</span><button className="icon-btn" aria-label="다음 추천 게임" onClick={() => move(1)}>{c.icon('ChevronRight')}</button></div><span className="sr-only" aria-live="polite">{game.title}</span></section>;
}