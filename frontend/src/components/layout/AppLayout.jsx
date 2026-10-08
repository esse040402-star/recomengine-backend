import { useEffect, useRef } from 'react';
import { useView } from '../../state/ViewContext';
import BrandLogo from './BrandLogo';
import Modal from '../common/Modal';
export default function AppLayout({
  children
}) {
  const c = useView(),
    main = useRef(null),
    onboarding = c.forceOnboarding || (!c.state.quick?.completed && !c.accountUser);
  useEffect(() => {
    document.documentElement.dataset.mode = c.state.mode;
    document.documentElement.dataset.theme = c.state.mode;
    document.documentElement.classList.toggle('collapsed', c.state.collapsed);
    document.body.classList.toggle('onboarding', onboarding);
    document.body.classList.toggle('menu-open', c.menuOpen);
    document.documentElement.dataset.gameTheme = c.state.home.style === 'brand' ? 'brand' : c.gameRoute()?.id || (c.route === 'home' ? c.state.home.style === 'fixed' ? c.state.home.game : c.list()[0]?.id : 'brand');
  }, [c.state.mode, c.state.collapsed, c.state.home, c.route, c.menuOpen, onboarding]);
  useEffect(() => {
    if (!matchMedia('(prefers-reduced-motion: reduce)').matches) main.current?.animate([{
      opacity: 0,
      transform: 'translateY(8px)'
    }, {
      opacity: 1,
      transform: 'translateY(0)'
    }], {
      duration: 320,
      easing: 'ease-out'
    });
  }, [c.route]);
  useEffect(() => {
    if(c.accountUser && c.auth.status==='error') c.toast('계정 저장에 실패했어요. 개인 페이지 설정에서 다시 저장할 수 있습니다.');
  },[c.auth.status]);
  useEffect(() => {
    if (!c.toastKey) return;
    const timer = setTimeout(() => c.setUI({
      toastMessage: null
    }), 3600);
    return () => clearTimeout(timer);
  }, [c.toastKey]);
  useEffect(() => {
    if (c.route !== 'home' || c.dialog) return;
    let frame = 0,
      busy = false;
    const wheel = e => {
      if (e.ctrlKey || Math.abs(e.deltaY) < 8 || e.target.closest('textarea,select,.guided-question')) return;
      const hero = main.current?.querySelector('.hero-carousel');
      if (!hero) return;
      const target = hero.getBoundingClientRect().top + scrollY - 100,
        start = scrollY;
      if (busy) {
        e.preventDefault();
        return;
      }
      if (e.deltaY > 0 && start < target - 20 || e.deltaY < 0 && start > 0 && start <= target + 50) {
        e.preventDefault();
        const end = e.deltaY > 0 ? target : 0;
        if (matchMedia('(prefers-reduced-motion: reduce)').matches) {
          scrollTo(0, end);
          return;
        }
        busy = true;
        const now = performance.now();
        const tick = t => {
          const p = Math.min(1, (t - now) / 920),
            ease = p < .5 ? 4 * p * p * p : 1 - (-2 * p + 2) ** 3 / 2;
          scrollTo({
            top: start + (end - start) * ease,
            behavior: 'instant'
          });
          if (p < 1) frame = requestAnimationFrame(tick);else busy = false;
        };
        frame = requestAnimationFrame(tick);
      }
    };
    window.addEventListener('wheel', wheel, {
      passive: false
    });
    return () => {
      window.removeEventListener('wheel', wheel);
      cancelAnimationFrame(frame);
    };
  }, [c.route, !!c.dialog]);
  return <><div className="ambient" aria-hidden="true" /><aside className="sidebar" id="sidebar" inert={!!c.dialog}><a className="brand sidebar-brand" href="#/home" aria-label="RecomEngine 홈"><BrandLogo collapsed={c.state.collapsed} /></a><div className="sidebar-cap">{c.btn(c.icon(c.state.collapsed ? 'ChevronRight' : 'ChevronLeft'), 'collapse', 'icon-btn', `aria-label="메뉴 ${c.state.collapsed ? '펼치기' : '접기'}" aria-expanded="${!c.state.collapsed}"`)}</div><nav className="nav" aria-label="주 메뉴">{[['home', 'House', '게임 추천'], ['explore', 'Search', '게임 탐색'], ['rankings', 'ChartNoAxesColumnIncreasing', '게임 랭킹'], ['news', 'Newspaper', '게임 뉴스']].map(([route, icon, label], itemIndex) => <button key={route} className={'nav-button ' + (c.route === route ? 'active' : '')} onClick={() => c.goto(route)} aria-label={label} title={label}>{c.icon(icon)}<span>{label}</span></button>)}</nav></aside><div className="shell"><header className="topbar" id="topbar" inert={!!c.dialog}><div className="top-identity">{!onboarding && c.btn(c.icon('Menu'), 'menu', 'icon-btn mobile-menu', 'aria-label="메뉴 열기"')}<a className="brand header-brand" href={onboarding ? '#/welcome' : '#/home'} aria-label="RecomEngine 홈"><BrandLogo /></a></div>{!onboarding && c.routeBtn(c.icon('UserRound'), 'profile', 'profile-entry')}</header><main className="main" tabIndex={-1} id="main" ref={main} data-screen={c.route.split('/')[0]} inert={!!c.dialog}>{children}</main></div>{c.dialog && <Modal />}{c.toastKey && c.toastMessage && <div id="toast-root"><div className="toast" role="status">{c.toastMessage}</div></div>}</>;
}