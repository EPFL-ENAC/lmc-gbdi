<template>
  <!-- Time, for two buildings: the whole life as it happens, per m² of gross floor area,
       both lines on one chart. Upfront is the part already spent the day each opens. -->
  <q-page class="page-grid">
    <p v-if="error" class="gbdi-card" role="alert">The buildings could not be loaded. {{ error }}</p>
    <p v-else-if="a === null || b === null" class="u-text-muted">Loading both buildings…</p>

    <template v-else>
      <header>
        <p class="time__name">
          <span class="time__swatch time__swatch--a" />{{ projectName(a) }} and
          <span class="time__swatch time__swatch--b" />{{ projectName(b) }}
        </p>
        <!-- Each figure in its building's colour, in the order of the names above. -->
        <h1 class="time__statement">
          <span class="time__figure--a">{{ figure(lines[0]!.upfront, kg) }}</span> and
          <span class="time__figure--b">{{ figure(lines[1]!.upfront, kg) }}</span> kg CO₂e per m<sup>2</sup>
          <span class="text-display-lead">spent before anyone moves in.</span>
        </h1>
        <p class="text-lead">
          {{ shareSentence(a) }} {{ shareSentence(b) }}
        </p>
      </header>

      <section class="time__chart">
        <p v-if="!drawable" class="u-text-muted">
          A gross floor area is missing, so the two cannot be drawn per m².
        </p>
        <figure v-else class="over-time">
          <svg :viewBox="`0 0 ${W} ${H}`" class="over-time__plot" role="img" :aria-label="summary">
            <g class="over-time__grid">
              <line v-for="t in yTicks" :key="`y${t}`" :x1="L" :x2="xEnd" :y1="y(t)" :y2="y(t)" />
            </g>
            <line class="over-time__zero" :x1="L" :x2="xEnd" :y1="y(0)" :y2="y(0)" />
            <line class="over-time__boundary" :x1="xBoundary" :x2="xBoundary" :y1="T" :y2="H - B" />
            <g v-for="line in lines" :key="line.key" :class="`over-time__series over-time__series--${line.key}`">
              <polyline class="over-time__line" :points="points(line)" />
              <line
                class="over-time__beyond"
                :x1="xBeyond + (line.key === 'a' ? -4 : 4)"
                :x2="xBeyond + (line.key === 'a' ? -4 : 4)"
                :y1="y(line.wholeLife!)"
                :y2="y(line.wholeLife! + line.moduleD!)"
              />
              <circle :cx="x(line, 1)" :cy="y(line.wholeLife!)" r="4" />
              <!-- The figures on the line itself: upfront, whole life, module D. -->
              <g class="over-time__labels">
                <text :x="x(line, 0) + 8" :y="y(line.upfront!) - 8">{{ kg.format(line.upfront!) }} upfront</text>
                <text :x="x(line, 1) - 10" :y="y(line.wholeLife!) - 8" text-anchor="end">
                  {{ kg.format(line.wholeLife!) }} whole life
                </text>
                <text :x="xBeyond + 10" :y="y(line.wholeLife! + line.moduleD!) + 4">{{ kg.format(line.moduleD!) }}</text>
              </g>
            </g>
            <g class="over-time__axis">
              <text v-for="t in yTicks" :key="`yl${t}`" :x="L - 8" :y="y(t) + 4" text-anchor="end">
                {{ compact.format(t) }}
              </text>
              <text v-for="tick in xTicks" :key="tick.label" :x="tick.x" :y="H - B + 18" :text-anchor="tick.anchor">
                {{ tick.label }}
              </text>
              <text :x="xBeyond" :y="H - B + 18" text-anchor="middle">D</text>
            </g>
          </svg>
          <figcaption class="over-time__caption">
            <span v-for="line in lines" :key="line.key" class="time__legend">
              <span class="time__swatch" :class="`time__swatch--${line.key}`" />{{ line.name }}
            </span>
            Cumulative kg CO₂e per m² of gross floor area: a step at opening (A1–A5), a slope through use (B1–B8), a
            step at the end of life (C1–C4). Dashed beyond the line: module D, outside the total.
            {{ periodNote }}
          </figcaption>
        </figure>
      </section>

      <section class="time__section">
        <h2 class="time__title">Which elements carry the end of life</h2>
        <p class="u-text-muted">The step at the end comes from the elements whose C1–C4 is largest, per m² for each building.</p>
        <PairedBars
          :rows="endOfLifeRows"
          :a-label="a.code"
          :b-label="b.code"
          unit="kg CO₂e per m², C1–C4"
          caption="OpenBDF Tier 2 elements, then the rest of each building's C1–C4. A building without the element reads 0."
        />
      </section>
    </template>
  </q-page>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ComparedRow } from '@/api/buildings';
import type { Overview } from '@/api/overview';
import PairedBars from '@/components/PairedBars.vue';
import { pairRows, perM2, projectName } from '@/compare';
import { useOverviewPair, type NamedOverview } from '@/composables/useOverview';
import { figure, kg, percent } from '@/format';

const { a, b, error } = useOverviewPair();

const stage = (o: Overview, key: string) => o.stages.find((s) => s.key === key)?.gwp ?? 0;
const period = (o: Overview) => o.project.reference_study_period_years;

// Each building's life as per-m² figures; null throughout when the floor area is missing.
const lines = computed(() =>
  (a.value && b.value ? [a.value, b.value] : []).map((o, i) => ({
    key: i === 0 ? 'a' : 'b',
    name: projectName(o),
    period: period(o),
    upfront: perM2(o, o.headline.upfront),
    use: perM2(o, stage(o, 'b1_b8')),
    endOfLife: perM2(o, stage(o, 'c1_c4')),
    wholeLife: perM2(o, o.headline.whole_life),
    moduleD: perM2(o, o.headline.module_d1),
  })),
);
type Line = (typeof lines.value)[number];
const drawable = computed(() => lines.value.length === 2 && lines.value.every((l) => l.wholeLife !== null));

// Upfront near zero or below is not a low-carbon start: timber's stored (biogenic) carbon
// offsets what making the materials emits, until it is released at C3–C4.
// ponytail: "near zero" is A1–A3 under 5 % of the whole life; tune if real projects disagree.
const shareSentence = (o: NamedOverview) =>
  stage(o, 'a1_a3') < 0.05 * o.headline.whole_life
    ? `${projectName(o)}: timber's stored carbon offsets what making its materials emits, so little shows upfront; it is released again at the end of life.`
    : `${projectName(o)} spends ${percent.format(o.headline.upfront_share)} of its whole-life carbon upfront.`;

// Years when both declare a study period, one shared axis to the longer one. Otherwise
// the life is drawn as a sequence of moments, and the axis says so.
const years = computed(() => {
  const [pa, pb] = lines.value.map((l) => l.period);
  return pa && pb ? Math.max(pa, pb) : null;
});
const periodNote = computed(() =>
  years.value === null
    ? 'No common study period is declared, so the years of use are drawn as one span, not to scale.'
    : 'B1–B8 is spread evenly across the years, a simplification: replacements really happen in steps.',
);

// Chart geometry only.
const W = 1100;
const H = 420;
const [L, R, T, B] = [64, 110, 24, 40];
const xEnd = W - R - 48;
const xBoundary = xEnd + 24;
const xBeyond = xEnd + 48;
const compact = new Intl.NumberFormat(undefined, { notation: 'compact' });

// t runs 0 (opening) to 1 (end of this building's study period).
const x = (line: Line, t: number) => {
  const span = years.value === null ? 1 : line.period! / years.value;
  return L + t * span * (xEnd - L);
};
const domain = computed(() => {
  const values = lines.value.flatMap((l) => [0, l.upfront!, l.upfront! + l.use!, l.wholeLife!, l.wholeLife! + l.moduleD!]);
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const pad = (hi - lo) * 0.08;
  return [lo < 0 ? lo - pad : 0, hi + pad] as const;
});
const y = (value: number) => {
  const [lo, hi] = domain.value;
  return H - B - ((value - lo) / (hi - lo || 1)) * (H - B - T);
};
const yTicks = computed(() => {
  const [lo, hi] = domain.value;
  const step = niceCeiling((hi - lo) / 8);
  return Array.from({ length: Math.floor(hi / step) - Math.ceil(lo / step) + 1 }, (_, i) => (Math.ceil(lo / step) + i) * step);
});
const xTicks = computed(() => {
  const n = years.value;
  if (n === null) {
    return [
      { label: 'Opening', x: L, anchor: 'start' },
      { label: 'Years of use', x: (L + xEnd) / 2, anchor: 'middle' },
      { label: 'End of life', x: xEnd, anchor: 'end' },
    ];
  }
  return Array.from({ length: Math.floor(n / 10) + 1 }, (_, i) => ({
    label: i === 0 ? 'Year 0' : String(i * 10),
    x: L + ((i * 10) / n) * (xEnd - L),
    anchor: 'middle',
  }));
});
const points = (l: Line) =>
  [
    [x(l, 0), y(0)],
    [x(l, 0), y(l.upfront!)],
    [x(l, 1), y(l.upfront! + l.use!)],
    [x(l, 1), y(l.wholeLife!)],
  ]
    .map((p) => p.join(','))
    .join(' ');
const summary = computed(() =>
  lines.value
    .map((l) => `${l.name}: ${figure(l.upfront, kg)} kg per m² upfront, ${figure(l.wholeLife, kg)} over the whole life.`)
    .join(' '),
);

function niceCeiling(value: number) {
  const magnitude = 10 ** Math.floor(Math.log10(value || 1));
  const step = [1, 1.5, 2, 2.5, 5, 10].find((s) => s * magnitude >= value) ?? 10;
  return step * magnitude;
}

// The shown elements, then what they leave of C1–C4: other classified and not classified
// elements carry no stage split, so the remainder is theirs.
const endOfLife = (o: Overview) => {
  const rows = o.element_stages.map((e) => ({ label: e.element, c: e.gwp_by_stage['c1_c4'] ?? 0 }));
  const rest = stage(o, 'c1_c4') - rows.reduce((sum, r) => sum + r.c, 0);
  return [...rows, { label: 'Other and not classified', c: rest }];
};
const endOfLifeRows = computed<ComparedRow[]>(() =>
  a.value && b.value ? pairRows(a.value, b.value, endOfLife, (r) => r.label, (r) => r.c) : [],
);
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.time__name {
  margin: 0 0 tokens.$spacing-sm;
  font-size: tokens.$text-size-heading-lg;
}

.time__statement {
  margin: 0;
  font-size: tokens.$text-size-display-lg;
}

.time__statement .text-display-lead {
  display: block;
}

// SK Modernist has no ² glyph: a sized-down 2 instead.
.time__statement sup {
  font-size: 0.45em;
  line-height: 0;
}

.time__chart {
  padding: tokens.$spacing-xl;
  border: tokens.$border-width solid tokens.$color-border;
  border-radius: tokens.$radius-panel;
}

.over-time {
  margin: 0;
}

.over-time__plot {
  display: block;
  width: 100%;
  height: auto;
  font-family: tokens.$text-font-family;
  font-size: tokens.$text-size-xs;
}

.over-time__grid line {
  stroke: tokens.$dataviz-gridline;
}

.over-time__zero {
  stroke: tokens.$color-text-muted;
}

.over-time__boundary {
  stroke: tokens.$color-text-muted;
  stroke-dasharray: 4 4;
}

.over-time__line {
  fill: none;
  stroke-width: 2.5;
  stroke-linejoin: round;
}

.over-time__beyond {
  stroke-width: 2;
  stroke-dasharray: 2 3;
}

.over-time__series--a {
  stroke: var(--gbdi-dataviz-green-1);
  fill: var(--gbdi-dataviz-green-1);
}

.over-time__series--b {
  stroke: var(--gbdi-dataviz-blue-2);
  fill: var(--gbdi-dataviz-blue-2);
}

.over-time__axis text {
  fill: tokens.$dataviz-axis-text;
}

.over-time__caption {
  max-width: 48rem;
  padding-top: tokens.$spacing-sm;
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}

.time__legend {
  margin-right: tokens.$spacing-md;
  color: tokens.$color-text;
}

.time__swatch {
  display: inline-block;
  width: 0.75rem;
  height: 0.75rem;
  margin-right: tokens.$spacing-xs;
  vertical-align: -0.1rem;
}

.time__swatch--a {
  background: var(--gbdi-dataviz-green-1);
}

.time__swatch--b {
  background: var(--gbdi-dataviz-blue-2);
}

.time__figure--a {
  color: var(--gbdi-dataviz-green-1);
}

.time__figure--b {
  color: var(--gbdi-dataviz-blue-2);
}

.over-time__labels text {
  stroke: none;
  font-variant-numeric: tabular-nums;
}

.time__section {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-md;
  padding-top: tokens.$spacing-xl;
  border-top: tokens.$border-width solid tokens.$color-border;
}

.time__section p {
  margin: 0;
}

.time__title {
  margin: 0;
  font-family: tokens.$text-font-family;
  font-size: tokens.$text-size-heading-lg;
}
</style>
