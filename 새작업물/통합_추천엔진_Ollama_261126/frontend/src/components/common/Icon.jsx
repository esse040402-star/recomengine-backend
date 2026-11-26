import React from 'react';
import icons from '../../data/generated/icons.json';
const props=a=>Object.fromEntries(Object.entries(a).map(([k,v])=>[k.replace(/-([a-z])/g,(_,c)=>c.toUpperCase()),v]));
const node=(n,i)=>React.createElement(n.tag,{...props(n.attrs),key:i},n.children.map(node));
export default function Icon({name}){const s=icons.find(x=>x.attrs.id==='i-'+name);return <svg className="i" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{s?.children.map(node)}</svg>}
