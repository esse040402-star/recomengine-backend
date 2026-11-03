import {useState,useEffect,useRef} from 'react';
import {apiEnabled} from '../services/transport';
import {marketSnapshot,getStatus,getMarket,getReviews,getDetails} from '../services/steamService';
export default function useSteamData(route) {
  const [market,setMarket]=useState(()=>structuredClone(marketSnapshot));
  const [online,setOnline]=useState(false),[busy,setBusy]=useState(null),[details,setDetails]=useState({});
  const [panels,setPanels]=useState({}),[dates,setDates]=useState({rankings:marketSnapshot.capturedAt,news:marketSnapshot.capturedAt,reviews:{}}),[newsDates,setNewsDates]=useState({});
  const current=useRef({}),jobs=useRef({}),marketJob=useRef(null),detailJobs=useRef({});
  const panel=id=>current.current[id]||{filters:{sentiment:'all',language:'all',sort:'recent',days:'all'},live:null,cursor:null,count:12,busy:false,error:'',checkedAt:null};
  const update=(id,value)=>{current.current={...current.current,[id]:value};setPanels(current.current);};
  useEffect(()=>{
    if(!apiEnabled)return;
    const controller=new AbortController();
    getStatus({signal:controller.signal}).then(value=>{if(!controller.signal.aborted)setOnline(value?.feeds===true);}).catch(()=>{});
    return ()=>controller.abort();
  },[]);
  useEffect(()=>()=>{Object.values(jobs.current).forEach(x=>x.abort());Object.values(detailJobs.current).forEach(x=>x.abort());marketJob.current?.abort();},[]);
  const gameId=route.match(/^game\/([a-z0-9-]+)/)?.[1];
  useEffect(()=>{
    if(!online||!gameId||details[gameId])return;
    const controller=new AbortController();detailJobs.current[gameId]=controller;
    getDetails(gameId,controller.signal).then(value=>{if(!controller.signal.aborted&&value?.details)setDetails(s=>({...s,[gameId]:value.details}));}).catch(()=>{});
    return ()=>controller.abort();
  },[gameId,online]);
  async function refreshMarket(section,id) {
    marketJob.current?.abort();const controller=new AbortController();marketJob.current=controller;setBusy(section);
    try {
      const result=await getMarket(section,id,controller.signal);
      if(controller.signal.aborted)return;
      setMarket(old=>section==='rankings'?{...old,rankings:result.data}:section==='reviews'?{...old,reviews:{...old.reviews,[id]:result.data}}:{...old,...result.data,news:id?[...old.news.filter(x=>x.game!==id),...result.data.news]:result.data.news});
      if(section==='news'&&id)setNewsDates(s=>({...s,[id]:result.updatedAt}));
      else setDates(s=>section==='reviews'?{...s,reviews:{...s.reviews,[id]:result.updatedAt}}:{...s,[section]:result.updatedAt});
    }catch(error){if(!controller.signal.aborted)throw error;}
    finally{if(marketJob.current===controller)setBusy(null);}
  }
  async function fetchReviews(id,more=false,filters=panel(id).filters) {
    jobs.current[id]?.abort();const controller=new AbortController();jobs.current[id]=controller;
    const old=panel(id),cursor=more?old.cursor:'*';
    if(more&&!cursor)return;
    update(id,{...old,filters,busy:true,error:'',...(more?{}:{live:null,cursor:null,count:12})});
    try{
      const result=await getReviews(id,filters,cursor,controller.signal);
      if(controller.signal.aborted)return;
      const items=[...(more?old.live||[]:[]),...(result.items||[])];
      const unique=[...new Map(items.map(r=>[r.id||r.url,r])).values()];
      update(id,{...panel(id),live:unique,cursor:result.cursor&&result.cursor!==cursor&&result.items?.length?result.cursor:null,checkedAt:result.checkedAt,busy:false,count:unique.length});
    }catch(error){if(!controller.signal.aborted)update(id,{...panel(id),busy:false,error:error.message});}
  }
  function changeReview(id,key,value){
    const filters={...panel(id).filters,[key]:value};
    update(id,{...panel(id),filters,live:null,cursor:null,count:12,error:''});
    if(online)void fetchReviews(id,false,filters);
  }
  function moreReviews(id){const p=panel(id);if(p.busy)return;if(p.cursor&&online)void fetchReviews(id,true);else update(id,{...p,count:p.count+12});}
  return {market,online,busy,details,panels,dates,newsDates,panel,refreshMarket,fetchReviews,changeReview,moreReviews};
}
