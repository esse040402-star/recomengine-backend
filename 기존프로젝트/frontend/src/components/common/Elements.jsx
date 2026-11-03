import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useView } from '../../state/ViewContext';
export function ActionButton({
  children,
  onClick,
  ...props
}) {
  const ctx = useView();
  return <button type="button" {...props} onClick={e => {
    if (props['aria-disabled'] === true || props['aria-disabled'] === 'true') return;
    onClick?.(e);
    if (props['data-route']) ctx.goto(props['data-route']);else if (props['data-action']) ctx.action(props['data-action'], {
      id: props['data-id'],
      value: props['data-value'],
      kind: props['data-kind']
    }, e);
  }}>{children}</button>;
}
export function Anchor({
  href = '',
  children,
  ...props
}) {
  return href.startsWith('#') ? <Link to={href.slice(1) || '/home'} {...props}>{children}</Link> : <a href={href} {...props}>{children}</a>;
}
export function GameImage({
  src,
  alt = '',
  ...props
}) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [src]);
  return <img {...props} src={failed ? '/assets/image-fallback.svg' : src} alt={alt} onError={() => setFailed(true)} />;
}
export function Field({
  value,
  defaultChecked,
  checked,
  ...props
}) {
  const ctx = useView();
  const isSearch = props.id === 'explore-search';
  return <input {...props} {...isSearch ? {
    value: ctx.exploreState.query,
    onChange: e => ctx.changeExplore('query', e.target.value)
  } : {
    defaultValue: value,
    defaultChecked: checked ?? defaultChecked
  }} ref={el => {
    if (props.id) ctx.fields.current[props.id] = el;
  }} />;
}
export function FieldArea(props) {
  return <textarea {...props} />;
}
export function Form({
  children,
  id,
  onSubmit,
  ...props
}) {
  const ctx = useView();
  return <form {...props} id={id} ref={el => {
    if (id) ctx.forms.current[id] = el;
  }} onSubmit={e => {
    e.preventDefault();
    if (onSubmit) onSubmit(e);else ctx.submit(id, e);
  }}>{children}</form>;
}
export function Select({
  children,
  value,
  ...props
}) {
  return <select {...props} defaultValue={value}>{children}</select>;
}