import { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { useView } from '../../state/ViewContext';
export default function Modal() {
  const c = useView(),
    ref = useRef(null);
  useEffect(() => {
    const prev = document.activeElement;
    document.body.style.overflow = 'hidden';
    ref.current?.querySelector('button')?.focus();
    const key = e => {
      if (e.key === 'Escape') c.closeDialog();
      if (e.key === 'Tab') {
        const a = [...ref.current.querySelectorAll('button:not([disabled]),input,select,textarea,a[href]')];
        if (e.shiftKey && document.activeElement === a[0]) {
          e.preventDefault();
          a.at(-1)?.focus();
        } else if (!e.shiftKey && document.activeElement === a.at(-1)) {
          e.preventDefault();
          a[0]?.focus();
        }
      }
    };
    document.addEventListener('keydown', key);
    return () => {
      document.body.style.overflow = '';
      document.removeEventListener('keydown', key);
      prev?.focus();
    };
  }, []);
  const {
    name,
    params
  } = c.dialog;
  let d;
  if (name === 'profile-track') d = {
    title: '게임이 익숙하신가요?',
    body: <div className="dialog-body">{c.btn('게이머예요', 'profile-track', 'btn', 'data-value="gamer"')}{c.btn('비게이머예요', 'profile-track', 'btn', 'data-value="nongamer"')}</div>
  };else if (name === 'guided-save') d = {
    title: '이번 답변을 저장할까요?',
    body: <p className="dialog-body">기존 프로필 30문항은 유지하고 이번 추천 답변을 반영합니다.</p>,
    footer: c.btn('반영하기', 'guided-confirm-save', 'btn primary')
  };else d = c[name](params.kind ?? params.id ?? params.signup);
  if (!d) return null;
  return createPortal(<div className="dialog-backdrop" onClick={e => {
    if (e.target === e.currentTarget) c.closeDialog();
  }}><section className="dialog" ref={ref} role="dialog" aria-modal="true" aria-labelledby="dialog-title"><header className="dialog-header"><h2 id="dialog-title">{d.title}</h2>{c.btn(c.icon('X'), 'close', 'icon-btn', 'aria-label="창 닫기"')}</header>{d.body}{d.footer && <footer className="dialog-footer">{d.footer}</footer>}</section></div>, document.body);
}