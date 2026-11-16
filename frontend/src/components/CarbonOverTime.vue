<template>
  <!-- What each moment of the life emits, on one scale (review #81): a peak at year 0
       (A1–A5), a flat band through the years of use (B1–B8, per year), a peak at the
       end of life (C1–C4); beyond a dashed boundary, module D (D1 + D2), outside the total. -->
  <figure class="over-time">
    <ul class="over-time__legend">
      <li v-for="stage in shown" :key="stage.key">
        <span class="over-time__swatch" :style="{ background: stageColor(stage.key) }" /><Term :name="stage.label" />
      </li>
      <li v-if="moduleD"><span class="over-time__swatch over-time__swatch--credit" />Module D, outside the total</li>
    </ul>
    <div role="img" :aria-label="summary" :style="{ minHeight: height }">
      <EChart :option="option" :height="height" />
    </div>
    <figcaption class="over-time__caption">
      {{ units.time }} each moment emits, on one scale.
      <template v-if="has('b1_b8')">
        B1–B8 is spread evenly over the {{ period }} years, a simplification: replacements really happen in steps.
      </template>
      <template v-if="moduleD">Past the dashed boundary: module D, outside the total.</template>
    </figcaption>
  </figure>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useQuasar } from 'quasar';
import type { ComposeOption } from 'echarts/core';
import type { CustomSeriesOption } from 'echarts/charts';
import type { GridComponentOption, TooltipComponentOption } from 'echarts/components';
import type { ModuleD, StageTotal, Units } from '@/api/overview';
import Term from '@/components/atoms/Term.vue';
import { asyncEChart, cssColor } from '@/components/atoms/echarts';
import { shownStages, stageColor } from '@/dataviz';
import { amount } from '@/format';

const EChart = asyncEChart(() => import('@/components/atoms/echart-custom'));

const props = defineProps<{
  stages: StageTotal[]; // A1–A3, A4–A5, B1–B8, C1–C4, in that order
  upfront: number; // A1–A5
  usePerYear: number;
  moduleD: ModuleD | null; // null: the workbook has no module D, nothing drawn past the end
  period: number;
  units: Units;
}>();
const num = computed(() => amount(props.units));
const d = computed(() => props.moduleD?.module_d ?? 0); // D1 + D2, summed by the backend
const shown = computed(() => shownStages(props.stages));
const has = (key: string) => shown.value.some((s) => s.key === key);
const hasUpfront = computed(() => has('a1_a3') || has('a4_a5'));

const $q = useQuasar();
const phone = computed(() => $q.screen.lt.sm);
const height = computed(() => (phone.value ? '280px' : '360px'));
const compact = new Intl.NumberFormat(undefined, { notation: 'compact' });

const gwp = (key: string) => props.stages.find((s) => s.key === key)?.gwp ?? 0;
const endOfLife = computed(() => gwp('c1_c4'));

// Year 0 stacks A1–A3 and A4–A5; the rest are single parts from zero. Module D comes last.
const parts = computed(() => {
  const a13 = gwp('a1_a3');
  const a45 = gwp('a4_a5');
  const stacked = Math.sign(a13) === Math.sign(a45) ? a13 : 0; // ponytail: opposite signs both start at zero
  const t = props.units.time;
  const f = num.value;
  const drawn = [
    { key: 'a1_a3', from: 0, to: a13, tip: [`A1–A3: ${f.format(a13)} ${t}`] },
    { key: 'a4_a5', from: stacked, to: stacked + a45, tip: [`A4–A5: ${f.format(a45)} ${t}`] },
    { key: 'b1_b8', from: 0, to: props.usePerYear, tip: [`B1–B8: about ${f.format(props.usePerYear)} ${t} a year`] },
    { key: 'c1_c4', from: 0, to: endOfLife.value, tip: [`C1–C4: ${f.format(endOfLife.value)} ${t}`] },
  ].filter((part) => has(part.key));
  const m = props.moduleD;
  return m
    ? [
        ...drawn,
        {
          key: 'd',
          from: 0,
          to: d.value,
          tip: [
            `Module D: ${f.format(d.value)} ${t}, outside the total.`,
            `D1, material recovery: ${f.format(m.module_d1)}`,
            `D2, exported utilities: ${f.format(m.module_d2)}`,
          ],
        },
      ]
    : drawn;
});

// Names only what is drawn.
const summary = computed(() => {
  const f = num.value;
  const said = [
    hasUpfront.value && `${f.format(props.upfront)} at year 0`,
    has('b1_b8') && `about ${f.format(props.usePerYear)} a year in use`,
    has('c1_c4') && `${f.format(endOfLife.value)} at the end of life`,
    props.moduleD && `module D, ${f.format(d.value)}, beyond it, outside the total`,
  ].filter(Boolean);
  return `What each moment emits over ${props.period} years, in ${props.units.time}: ${said.join(', ')}.`;
});

// Workbook figures only, but the tooltip is still built as text, never as HTML.
function tip(i: number) {
  const box = document.createElement('div');
  for (const text of parts.value[i]?.tip ?? []) box.appendChild(document.createElement('div')).append(text);
  return box;
}

type Box = { x: number; y: number; width: number; height: number };

// The moments across the plot, in pixels, so a peak keeps its width on a phone too: a peak
// at year 0, the years of use between the two peaks, the end of life, then module D past a
// dashed boundary (without module D, the end of life takes its place).
function columns({ x, width }: Box) {
  const narrow = phone.value;
  const bar = narrow ? 28 : 44; // a peak's width: one moment, not a span of years
  const right = x + width;
  const xD = right - bar;
  const xBoundary = xD - (narrow ? 24 : 140); // room for the module D label
  const xEnd = props.moduleD ? xBoundary - (narrow ? 12 : 24) - bar : xD;
  return { narrow, bar, xD, xBoundary, xEnd, xUse: x + bar };
}

const option = computed((): ComposeOption<CustomSeriesOption | GridComponentOption | TooltipComponentOption> => {
  const muted = cssColor('var(--gbdi-color-text-muted)');
  const ink = cssColor('var(--gbdi-color-text)');
  const axisText = cssColor('var(--gbdi-dataviz-axis-text)');
  const f = num.value;
  const fills = parts.value.map((part) => (part.key === 'd' ? 'none' : cssColor(stageColor(part.key))));
  const text = (x: number, y: number, value: string, align: 'left' | 'center' | 'right', fill = ink, fontSize = 14) => ({
    type: 'text' as const,
    silent: true,
    style: { x, y, text: value, align, verticalAlign: (fontSize === 12 ? 'top' : 'middle') as 'top' | 'middle', fill, fontSize },
  });
  return {
    grid: { left: 8, right: 16, top: 24, bottom: phone.value ? 40 : 32 },
    xAxis: {
      type: 'value',
      min: 0,
      max: 1,
      axisLabel: { show: false },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLine: { onZero: true, lineStyle: { color: axisText } },
    },
    // One scale for every part, zero included, so a negative credit or year shows below it.
    yAxis: { type: 'value', axisLabel: { formatter: (v: number) => compact.format(v || 0) } },
    tooltip: {
      trigger: 'item',
      // The default triggerOn, mousemove|click, also opens it on a tap.
      confine: true,
      formatter: (params) => tip([params].flat()[0]?.dataIndex ?? 0),
    },
    series: [
      {
        type: 'custom',
        clip: false,
        // One item per part, then one silent item for the boundary, the moments and the notes.
        // Each item carries its two ends, so the y scale takes in every value.
        data: [...parts.value.map((part) => [0.5, part.from, part.to]), [0.5, 0, 0]],
        encode: { x: 0, y: [1, 2] },
        renderItem: (params, api) => {
          const box = params.coordSys as unknown as Box;
          const c = columns(box);
          const y = (value: number) => api.coord([0, value])[1];
          const part = parts.value[params.dataIndex];
          if (part) {
            const [x, width] = {
              a1_a3: [box.x, c.bar],
              a4_a5: [box.x, c.bar],
              b1_b8: [c.xUse, c.xEnd - c.xUse],
              c1_c4: [c.xEnd, c.bar],
              d: [c.xD, c.bar],
            }[part.key as 'd'];
            const credit = part.key === 'd';
            return {
              type: 'rect',
              shape: { x, y: Math.min(y(part.from), y(part.to)), width, height: Math.max(Math.abs(y(part.to) - y(part.from)), 1) },
              // Module D is outside the total: an outline, never a fill.
              style: credit ? { fill: 'none', stroke: muted, lineWidth: 2, lineDash: [4, 3] } : { fill: fills[params.dataIndex] },
            };
          }
          // The moments under the axis, on two lines on a phone. The notes beside the bars
          // only above it: on a phone they collide, and each figure stays in the tooltip, the
          // summary and the moments listed under the chart (TimeSection).
          const when = (first: string, second: string) => (c.narrow ? `${first}\n${second}` : `${first} ${second}`);
          const notes = !c.narrow;
          const below = box.y + box.height + 6;
          const mid = (c.xUse + c.xEnd) / 2;
          const children = [
            hasUpfront.value && text(box.x + c.bar / 2, below, when('Year', '0'), 'center', axisText, 12),
            notes && hasUpfront.value && text(box.x + c.bar + 8, y(props.upfront), `A1–A5: ${f.format(props.upfront)}`, 'left'),
            has('b1_b8') && text(mid, below, when('Years', `1 to ${props.period}`), 'center', axisText, 12),
            notes && has('b1_b8') && text(mid, y(Math.max(props.usePerYear, 0)) - 12, `B1–B8: about ${f.format(props.usePerYear)} a year`, 'center'),
            has('c1_c4') && text(c.xEnd + c.bar / 2, below, when('Year', String(props.period)), 'center', axisText, 12),
            notes && has('c1_c4') && text(c.xEnd - 8, y(endOfLife.value), `C1–C4: ${f.format(endOfLife.value)}`, 'right'),
            props.moduleD && text(c.xD + c.bar / 2, below, 'Beyond', 'center', axisText, 12),
            notes && props.moduleD && text(c.xD - 8, y(d.value), `Module D: ${f.format(d.value)}`, 'right'),
            props.moduleD && {
              type: 'line' as const,
              silent: true,
              shape: { x1: c.xBoundary, y1: box.y, x2: c.xBoundary, y2: box.y + box.height },
              style: { stroke: muted, lineDash: [4, 4] },
            },
          ].filter((child) => !!child);
          return { type: 'group', silent: true, children };
        },
      },
    ],
  };
});
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.over-time {
  margin: 0;
}

.over-time__legend {
  display: flex;
  flex-wrap: wrap;
  gap: tokens.$spacing-lg;
  margin: 0 0 tokens.$spacing-sm;
  padding: 0;
  list-style: none;
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}

.over-time__legend li {
  display: flex;
  align-items: center;
  gap: tokens.$spacing-xs;
}

.over-time__swatch {
  width: tokens.$spacing-md;
  height: tokens.$spacing-md;
  border-radius: tokens.$radius-xs;
}

.over-time__swatch--credit {
  border: 2px dashed tokens.$color-text-muted;
}

.over-time__caption {
  max-width: 42rem;
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}
</style>
