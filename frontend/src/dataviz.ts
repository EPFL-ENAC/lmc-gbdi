import type { Headline } from '@/api/overview';

// Life-cycle stage colours, A1–A3 → C1–C4: all greens, so orange is free for
// highlights (review #81). A pastel stage would vanish on a grey panel.
export const STAGE_COLORS = [
  'var(--gbdi-dataviz-green-1)',
  'var(--gbdi-dataviz-green-2)',
  'var(--gbdi-dataviz-green-3)',
  'var(--gbdi-dataviz-end-of-life)',
];
const STAGE_KEYS = ['a1_a3', 'a4_a5', 'b1_b8', 'c1_c4'];
// The colour follows the stage, not its position, so C keeps its colour when B is left out.
export const stageColor = (key: string) => STAGE_COLORS[STAGE_KEYS.indexOf(key)];

// org#89: leave out a stage or module D the workbook does not have (the backend's
// `present` and `module_d_present`). false restores the display that shows every
// stage and module D.
export const HIDE_ABSENT = true;
export const shownStages = <T extends { present: boolean }>(stages: T[]) =>
  HIDE_ABSENT ? stages.filter((s) => s.present) : stages;
export const showModuleD = (h: Pick<Headline, 'module_d_present'>) => !HIDE_ABSENT || h.module_d_present;

// Ten materials, one colour each, the same in every chart of a page. Neighbours in
// the walls differ in hue and in step, a dark one next to a bright or light one
// (org#97): three darks in a row read as one. Light green is left out, too close to
// the Green-Grey that stands for every other material.
export const MATERIAL_COLORS = [
  'var(--gbdi-dataviz-green-1)',
  'var(--gbdi-dataviz-orange-2)',
  'var(--gbdi-dataviz-blue-1)',
  'var(--gbdi-dataviz-purple-3)',
  'var(--gbdi-dataviz-green-2)',
  'var(--gbdi-dataviz-orange-1)',
  'var(--gbdi-dataviz-blue-3)',
  'var(--gbdi-dataviz-purple-1)',
  'var(--gbdi-dataviz-blue-2)',
  'var(--gbdi-dataviz-orange-3)',
];
export const OTHER_COLOR = 'var(--gbdi-color-surface-highlight)';

