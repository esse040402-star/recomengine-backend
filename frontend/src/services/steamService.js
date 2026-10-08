import snapshot from '../data/generated/marketSnapshot.json';
import reviews from '../data/generated/steamReviews.json';
import {request} from './transport';
export const marketSnapshot=snapshot;
export const reviewSnapshot=reviews;
export const getStatus=options=>request('/api/status',{timeout:2500,...options});
export const getMarket=(section,game,signal)=>request('/api/market?'+new URLSearchParams({section,...(game?{game}:{})}),{timeout:22000,signal});
export const getReviews=(game,filters={},cursor='*',signal)=>request('/api/steam/reviews?'+new URLSearchParams({game,...filters,cursor}),{timeout:22000,signal});
export const getDetails=(game,signal)=>request('/api/steam/details?'+new URLSearchParams({game}),{timeout:22000,signal});
