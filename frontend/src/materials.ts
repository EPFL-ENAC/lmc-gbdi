import type { MaterialHotspot } from '@/api/overview';

// The material lists every layout draws: a top 10, ranked by mass or by carbon, and
// the rest of `Overview.materials` on request.
export const TOP_MATERIALS = 10;
export type RankBy = 'mass' | 'carbon';
export const RANKINGS: { label: string; value: RankBy }[] = [
  { label: 'Top 10 by carbon', value: 'carbon' },
  { label: 'Top 10 by mass', value: 'mass' },
];

type Pair = { material: string; epd_product: string };
export const pairKey = (m: Pair) => `${m.material}|${m.epd_product}`;
export const materialLabel = (m: Pair) => m.material || m.epd_product;

export const ranked = (materials: MaterialHotspot[], by: RankBy) =>
  [...materials].sort((a, b) => (by === 'mass' ? b.mass_kg - a.mass_kg : b.gwp - a.gwp));

// What a top list leaves out, in the same ranking.
export const remaining = (materials: MaterialHotspot[], shown: Pair[], by: RankBy) => {
  const keys = new Set(shown.map(pairKey));
  return ranked(materials, by).filter((m) => !keys.has(pairKey(m)));
};
