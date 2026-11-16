// The material lists: a top 10, ranked by mass or by carbon, and the rest on request.
export type RankBy = 'mass' | 'carbon';
export const RANKINGS: { label: string; value: RankBy }[] = [
  { label: 'By mass', value: 'mass' },
  { label: 'By carbon', value: 'carbon' },
];

type Pair = { material: string; epd_product: string };
export const pairKey = (m: Pair) => `${m.material}|${m.epd_product}`;
export const materialLabel = (m: Pair) => m.material || m.epd_product;
