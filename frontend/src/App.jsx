import {useEffect} from 'react';
import {ViewContext} from './state/ViewContext';
import usePageController from './hooks/usePageController';
import AppLayout from './components/layout/AppLayout';
import {resolveRoute} from './utils/routes';
function Page({c}) {
  if(c.route.startsWith('survey/'))return c.survey(c.route.split('/')[1]);
  if(c.route.startsWith('game/'))return c.gamePage();
  const pages={welcome:'welcome',home:'home',result:'quickResult','deep-intro':'deepIntro',explore:'exploreScreen',rankings:'rankings',news:'newsScreen',saved:'savedGames',profile:'profile',report:'reportScreen'};
  return c[pages[c.route]]();
}
export default function App() {
  const c=usePageController();
  const target=resolveRoute(c.route,{state:c.state,user:c.accountUser,forceOnboarding:c.forceOnboarding,gameExists:c.game,firstGame:c.list()[0]?.id});
  useEffect(()=>{if(c.auth.ready&&target!==c.route)c.goto(target);},[target,c.route,c.auth.ready]);
  return <ViewContext.Provider value={c}><AppLayout>{!c.auth.ready?<div className="empty" role="status">계정을 확인하고 있어요.</div>:target===c.route?<Page c={c}/>:null}</AppLayout></ViewContext.Provider>;
}
