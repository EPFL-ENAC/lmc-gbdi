<template>
  <!-- Mass against carbon, both on log scales: the diagonals are lines of equal carbon
       per kg, so a heavy, low-intensity material and a light, intense one read apart.
       The plot sits in a fixed box, the table beside it gives the figures. -->
  <p v-if="!rows.length" class="u-text-muted">No material carbon in this project.</p>
  <figure v-else class="intensity">
    <div class="intensity__body">
      <!-- No box at all when no row can sit on the log axes: the table holds the figures. -->
      <div v-if="plotted.length" role="img" :aria-label="summary" :style="{ minHeight: height }">
        <EChart ref="chart" :option="option" :height="height" @hover="onHover" />
      </div>
      <table class="intensity__table" aria-label="The top materials by carbon: mass, carbon and carbon per kg">
        <colgroup>
          <col class="intensity__col-rank" />
          <col />
          <col v-if="!phone" class="intensity__col-figure" />
          <col v-if="!phone" class="intensity__col-figure" />
          <col class="intensity__col-per-kg" />
        </colgroup>
        <thead>
          <tr>
            <th scope="col" class="num">#</th>
            <th scope="col">Material</th>
            <th v-if="!phone" scope="col" class="num">{{ units.mass }}</th>
            <th v-if="!phone" scope="col" class="num">{{ units.carbon }}</th>
            <th scope="col">{{ units.intensity }}</th>
          </tr>
        </thead>
        <tbody>
          <!-- Hover, focus or tap a row to light its dot; on a phone the tap also shows
               the mass and the carbon, whose columns are left out. -->
          <tr
            v-for="r in rows"
            :key="r.key"
            tabindex="0"
            :class="{ 'intensity__row--active': active === r.rank }"
            @mouseenter="active = r.rank"
            @mouseleave="active = null"
            @focus="active = r.rank"
            @blur="active = null"
            @click="active = r.rank"
          >
            <td class="num">{{ r.rank }}</td>
            <th scope="row" class="intensity__name" :title="r.name">
              {{ r.name }}
              <!-- Always in the page on a phone, so a screen reader reads it; shown on a tap. -->
              <span v-if="phone" class="intensity__more" :class="{ 'intensity__more--hidden': active !== r.rank }">
                {{ fmt.format(r.mass_kg) }} {{ units.mass }}, {{ fmt.format(r.gwp) }} {{ units.carbon }}
              </span>
            </th>
            <td v-if="!phone" class="num">{{ fmt.format(r.mass_kg) }}</td>
            <td v-if="!phone" class="num">{{ fmt.format(r.gwp) }}</td>
            <td class="intensity__per-kg">
              <span class="intensity__bar" :style="{ width: `${barWidth(r.gwp_per_kg)}px` }" />
              {{ figure(r.gwp_per_kg, three) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <figcaption class="intensity__caption">{{ caption }}</figcaption>
  </figure>
</template>

<script setup lang="ts">
import { computed, ref, useTemplateRef, watch } from 'vue';
import { useQuasar } from 'quasar';
import type { ComposeOption } from 'echarts/core';
import type { ScatterSeriesOption } from 'echarts/charts';
import type { GridComponentOption, MarkLineComponentOption, TooltipComponentOption } from 'echarts/components';
import type { MaterialHotspot, Units } from '@/api/overview';
import { asyncEChart } from '@/components/atoms/echarts';
import { amount, figure, kg, materialName, three } from '@/format';
import { materialLabel, pairKey } from '@/materials';

// ECharts loads with the chart only, in its own chunk, with the scatter pieces this chart
// registers. The empty state, the table, the caption and the summary stay outside it.
const EChart = asyncEChart(() => import('@/components/atoms/echart-scatter'));

const props = defineProps<{ hotspots: MaterialHotspot[]; units: Units }>(); // the top 10, by carbon

const $q = useQuasar();
const phone = computed(() => $q.screen.lt.sm);
const height = computed(() => (phone.value ? '220px' : '360px'));
const fmt = computed(() => amount(props.units));
const BAR = 48; // px, the per-kg bar of the largest intensity
const compact = new Intl.NumberFormat(undefined, { notation: 'compact' });
const ISO = [0.01, 0.1, 1, 10];

// Every figure comes from the backend, in its order; the rank is the position.
const rows = computed(() =>
  props.hotspots.map((h, i) => ({ ...h, rank: i + 1, key: pairKey(h), name: materialName(materialLabel(h)) })),
);
// A log axis cannot show zero or less: such a row keeps its figures in the table, without a dot.
const plotted = computed(() => rows.value.filter((r) => r.mass_kg > 0 && r.gwp > 0));
const skipped = computed(() => rows.value.length - plotted.value.length);

// One active rank drives both sides: a row lights its dot, a dot lights its row. The
// chart option never reads it, so a redraw does not depend on it.
const active = ref<number | null>(null);
const chart = useTemplateRef<{ highlight: (dataIndex: number | null) => void }>('chart');
const onHover = (dataIndex: number | null) => (active.value = dataIndex === null ? null : plotted.value[dataIndex]!.rank);
// A redraw (another basis, another naming) clears the chart's own highlight, so the
// option is a source too and the lit dot follows the lit row again.
watch([active, () => props.hotspots, () => props.units], ([rank]) => {
  const index = plotted.value.findIndex((r) => r.rank === rank);
  chart.value?.highlight(index < 0 ? null : index);
}, { flush: 'post' });

const maxPerKg = computed(() => Math.max(0, ...rows.value.map((r) => r.gwp_per_kg ?? 0)));
const barWidth = (v: number | null) => (v && v > 0 && maxPerKg.value > 0 ? (v / maxPerKg.value) * BAR : 0);

// Axis ends on powers of ten, so the diagonals cross whole decades.
// One decade of room on each side: a value on an exact power of ten stays off the edge,
// and one material alone still gets an axis with a span.
const bounds = (values: number[]) => [
  10 ** (Math.ceil(Math.log10(Math.min(...values))) - 1),
  10 ** (Math.floor(Math.log10(Math.max(...values))) + 1),
];
const xDomain = computed(() => bounds(plotted.value.map((r) => r.mass_kg)));
const yDomain = computed(() => bounds(plotted.value.map((r) => r.gwp)));

// GWP = k × mass is a straight diagonal in log-log; it ends where it leaves the plot.
const isoLines = computed(() => {
  const [xLo, xHi] = xDomain.value;
  const [yLo, yHi] = yDomain.value;
  return ISO.map((k) => ({ k, start: Math.max(xLo, yLo / k), end: Math.min(xHi, yHi / k) })).filter(
    (l) => l.start < l.end,
  );
});

// Material names come from uploaded workbooks: the tooltip is built with textContent,
// never as HTML.
function tip(index: number) {
  const r = plotted.value[index];
  if (!r) return '';
  const { units } = props;
  const box = document.createElement('div');
  const line = (text: string) => box.appendChild(document.createElement('div')).append(text);
  line(`${r.rank}. ${r.name}`);
  line(`Mass: ${fmt.value.format(r.mass_kg)} ${units.mass}`);
  line(`Carbon: ${fmt.value.format(r.gwp)} ${units.carbon}`);
  line(`Per kg: ${figure(r.gwp_per_kg, three)} ${units.intensity}`);
  return box;
}

const token = (name: string) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

const option = computed(
  (): ComposeOption<ScatterSeriesOption | GridComponentOption | MarkLineComponentOption | TooltipComponentOption> => {
    const { units } = props;
    const [xMin, xMax] = xDomain.value;
    const [yMin, yMax] = yDomain.value;
    const axisLabel = { formatter: (v: number) => compact.format(v) };
    return {
      grid: { left: 48, right: 16, top: 28, bottom: 40 },
      xAxis: {
        type: 'log',
        min: xMin,
        max: xMax,
        name: `Mass (${units.mass})`,
        nameLocation: 'middle',
        nameGap: 24,
        axisLabel,
      },
      yAxis: { type: 'log', min: yMin, max: yMax, name: `GWP (${units.carbon})`, nameLocation: 'end', axisLabel },
      tooltip: {
        trigger: 'item',
        // The default triggerOn, mousemove|click, also opens it on a tap.
        confine: true,
        formatter: (params) => tip([params].flat()[0]?.dataIndex ?? -1),
      },
      series: [
        {
          type: 'scatter',
          data: plotted.value.map((r) => ({ value: [r.mass_kg, r.gwp], rank: r.rank })),
          symbolSize: 18,
          itemStyle: { color: token('--gbdi-color-primary-strong') },
          label: {
            show: true,
            position: 'inside',
            formatter: (p) => String((p.data as { rank: number }).rank),
            color: token('--gbdi-color-text-on-primary'),
            fontWeight: 'bold',
          },
          emphasis: { focus: 'self', scale: 1.4, itemStyle: { color: token('--gbdi-color-accent') } },
          markLine: {
            silent: true,
            symbol: 'none',
            lineStyle: { type: 'dashed', color: token('--gbdi-illustration-stroke'), width: 1 },
            label: { position: 'insideEndTop', color: token('--gbdi-dataviz-axis-text') },
            data: isoLines.value.map((l) => [
              { coord: [l.start, l.k * l.start], name: `${l.k} ${units.intensity}` },
              { coord: [l.end, l.k * l.end] },
            ]),
          },
        },
      ],
    };
  },
);

const summary = computed(
  () =>
    `${plotted.value.length} materials by mass and carbon, on log scales; ` +
    'the table beside the plot gives the same figures.',
);
const caption = computed(
  () =>
    `The top ${rows.value.length} materials by carbon. A dot is one material, numbered by its rank. ` +
    `A dashed line is equal carbon per kg, in ${props.units.intensity}: a material above a line is more carbon intense.` +
    (skipped.value > 0
      ? ` No dot for ${kg.format(skipped.value)} ${skipped.value === 1 ? 'material' : 'materials'} with a zero or negative mass or carbon: a log scale cannot show them.`
      : ''),
);
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.intensity {
  margin: 0;
  container-type: inline-size;
}

// The plot keeps a fixed height, so its text keeps its size. It sits beside the table
// only when both fit; below that the table goes under it.
.intensity__body {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: tokens.$spacing-md;
  align-items: start;
}

@container (min-width: 1100px) {
  .intensity__body {
    grid-template-columns: 560px minmax(0, 1fr);
    gap: tokens.$spacing-xl;
  }
}

// A fixed layout, so a long workbook name ends in an ellipsis instead of widening the table.
.intensity__table {
  width: 100%;
  table-layout: fixed;
  border-collapse: collapse;
  font-size: tokens.$text-size-sm;
}

.intensity__table th,
.intensity__table td {
  padding: tokens.$spacing-xs tokens.$spacing-sm;
  border-bottom: 1px solid tokens.$color-border;
  text-align: left;
  white-space: nowrap;
}

.intensity__col-rank {
  width: 2.5rem;
}

.intensity__col-figure {
  width: 6.5rem;
}

.intensity__col-per-kg {
  width: 9rem;
}

.intensity__table thead th {
  white-space: normal;
  vertical-align: bottom;
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}

.intensity__table tbody th {
  font-weight: normal;
}

.intensity__table tbody tr {
  cursor: default;
}

.intensity__table tbody tr:focus-visible {
  outline: 2px solid tokens.$color-primary-strong;
  outline-offset: -2px;
}

.intensity__row--active > * {
  background: tokens.$color-surface-highlight;
}

.intensity__more {
  display: block;
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}

// Off screen for the eye, still read by a screen reader.
.intensity__more--hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

.intensity__table .num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.intensity__name {
  overflow: hidden;
  text-overflow: ellipsis;
}

.intensity__per-kg {
  font-variant-numeric: tabular-nums;
}

.intensity__bar {
  display: inline-block;
  height: 8px;
  margin-right: tokens.$spacing-xs;
  vertical-align: middle;
  background: tokens.$color-primary;
  border-radius: 2px;
}

.intensity__caption {
  margin-top: tokens.$spacing-sm;
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}

// On a phone (the width where `phone` hides the mass and carbon columns) the name
// wraps, even a name without spaces, and a tap shows the rest.
@media (max-width: tokens.$breakpoint-mobile-max) {
  .intensity__table .intensity__name {
    white-space: normal;
    overflow-wrap: anywhere;
  }

  .intensity__col-rank {
    width: 2rem;
  }

  .intensity__col-per-kg {
    width: 7.5rem;
  }
}
</style>
