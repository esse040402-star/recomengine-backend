import snapshot from '../data/generated/marketSnapshot.json';
import reviews from '../data/generated/steamReviews.json';
// TODO: FastAPI Steam API 연결. 화면은 이 스냅샷과 동일한 DTO만 사용함.
export const marketSnapshot=snapshot;
export const reviewSnapshot=reviews;
export const getMarket=async()=>structuredClone(snapshot);
export const getReviews=async id=>reviews.games[id]||{items:[]};
