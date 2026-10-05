import CATALOG from '../data/generated/catalog.json';
import GAME_DETAILS from '../data/generated/gameDetails.json';
import ASSETS from '../data/generated/prototypeAssets.generated';
export {CATALOG,GAME_DETAILS,ASSETS};
export const getGame=id=>CATALOG.find(g=>g.id===id);
export const getGameImage=(id,kind='card')=>ASSETS[id]?.[kind]||ASSETS[id]?.card||GAME_DETAILS[id]?.header||'/assets/image-fallback.svg';
// TODO: FastAPI → RAWG / IGDB / Steam 의 응답을 이 경계에서 공통 DTO로 변환합니다.
export async function getGameDetails(id){return GAME_DETAILS[id]||null;}
