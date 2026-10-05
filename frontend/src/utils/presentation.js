export const esc=x=>String(x??'');
export const style=text=>Object.fromEntries(String(text||'').split(';').filter(Boolean).map(x=>{const i=x.indexOf(':');return [(x.slice(0,i).trim().startsWith('--')?x.slice(0,i).trim():x.slice(0,i).trim().replace(/-([a-z])/g,(m,c)=>c.toUpperCase())),x.slice(i+1).trim()]}));
export function attrs(text){const out={};for(const m of String(text||'').matchAll(/([^\s=]+)(?:="([^"]*)"|'([^']*)')?/g)){let k=m[1],v=m[2]??m[3]??true;if(k==='style')v=style(v);if(k==='tabindex')k='tabIndex';if(k==='checked')k='defaultChecked';out[k]=v;}return out;}
export const safeSteamURL=(url,fallback='https://store.steampowered.com/')=>{try{const u=new URL(url);return u.protocol==='https:'?u.href:fallback}catch{return fallback}};
export const safeSteamImage=url=>typeof url==='string'&&(url.startsWith('/assets/')||url.startsWith('https://'))?url:'';
export const marketDate=value=>value?new Date(value).toLocaleString('ko-KR',{timeZone:'Asia/Seoul',month:'long',day:'numeric',hour:'2-digit',minute:'2-digit'}):'확인 시점 정보';
export const marketPrice=item=>!Number.isFinite(item.price)?'가격은 상점에서 확인':item.price===0?'무료':new Intl.NumberFormat('ko-KR',{style:'currency',currency:item.currency||'KRW',maximumFractionDigits:item.currency==='KRW'?0:2}).format(item.price/100);
