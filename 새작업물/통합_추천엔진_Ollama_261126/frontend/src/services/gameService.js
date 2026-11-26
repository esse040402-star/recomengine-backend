import CATALOG from '../data/generated/catalog.json';
import GAME_DETAILS from '../data/generated/gameDetails.json';
import ASSETS from '../data/generated/prototypeAssets.generated';
export {CATALOG,GAME_DETAILS,ASSETS};
export const getGame=id=>CATALOG.find(g=>g.id===id);
export const getGameImage=(id,kind='card')=>ASSETS[id]?.[kind]||ASSETS[id]?.card||GAME_DETAILS[id]?.header||'/assets/image-fallback.svg';
// TODO: FastAPI → RAWG / IGDB / Steam 의 응답을 이 경계에서 공통 DTO로 변환합니다.
export async function getGameDetails(id){return GAME_DETAILS[id]||null;}

// 외부 PC·콘솔 게임 검색 (기존 카탈로그와 별도 처리)
export async function searchExternalGames(query, { signal } = {}) {
  const keyword = query.trim();
  if (!keyword) return { items: [], total: 0 };

  const params = new URLSearchParams({
    q: keyword,
    page: '1',
    size: '20',
  });

  const response = await fetch(
    `/api/external-games?${params.toString()}`,
    { signal }
  );

  if (!response.ok) {
    throw new Error('외부 게임 검색에 실패했어요.');
  }

  return response.json();
}

// 외부 게임 상세정보 조회
export async function getExternalGameDetails(appid, { signal } = {}) {
  const response = await fetch(`/api/external-games/${encodeURIComponent(appid)}`, { signal });

  if (!response.ok) {
    throw new Error('외부 게임 상세정보를 불러오지 못했어요.');
  }

  return response.json();
}
