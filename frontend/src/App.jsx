import {useEffect} from 'react';
import {ViewContext} from './state/ViewContext';
import usePageController from './hooks/usePageController';
import AppLayout from './components/layout/AppLayout';
function Page({c}){const kind=c.route.split('/')[1];useEffect(()=>{if(c.route.startsWith('survey/')&&!c.draft(kind))c.goto('welcome')},[c.route]);if(c.route.startsWith('survey/'))return c.draft(kind)?c.survey(kind):null;if(c.route.startsWith('game/'))return c.gameRoute()&&c.game(c.gameRoute().id)?c.gamePage():<h1>게임을 찾을 수 없어요.</h1>;const pages={welcome:'welcome',home:'home',result:'quickResult','deep-intro':'deepIntro',explore:'exploreScreen',rankings:'rankings',news:'newsScreen',saved:'savedGames',profile:'profile',report:'reportScreen'};return c[pages[c.route]||'welcome']()}
export default function App(){const c=usePageController();useEffect(()=>{if(c.route==='welcome'&&(c.state.quick?.completed||c.accountUser))c.goto('home')},[c.route,c.state.quick?.completed,c.accountUser]);return <ViewContext.Provider value={c}><AppLayout><Page c={c}/></AppLayout></ViewContext.Provider>}
