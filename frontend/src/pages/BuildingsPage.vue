<template>
  <!-- Every stored building on one scale: kg CO₂e per m² of gross floor area, split by
       life-cycle stage around zero, so stored biogenic carbon reads as such. -->
  <q-page class="page-grid">
    <header class="buildings__head">
      <div>
        <h1>Buildings</h1>
        <p class="text-lead">
          OpenBDF workbooks read by lmc-openbdf. Whole-life carbon, modules A to C, per m² of gross floor area:
          the size of a building drops out, its design stays.
        </p>
      </div>
      <div>
        <q-btn unelevated no-caps color="primary" label="Add a workbook" :loading="upload?.state === 'reading'" @click="picker?.click()" />
        <input ref="picker" type="file" accept=".xlsx" hidden @change="onPick" />
      </div>
    </header>

    <section v-if="upload" class="gbdi-card upload" :role="upload.state === 'rejected' ? 'alert' : 'status'">
      <template v-if="upload.state === 'reading'">
        <p>
          Reading {{ upload.name }}. openbdf translates and validates every line: a COLA building takes 15 to 60
          seconds.
        </p>
        <q-linear-progress indeterminate color="primary" />
      </template>
      <p v-else-if="upload.state === 'added'">
        Added {{ upload.name }}: {{ kg.format(upload.building.rows_read) }} lines, {{ upload.building.findings }}
        warnings kept with it.
        <router-link class="link" :to="`/buildings/${upload.building.id}`">Open it</router-link>
      </p>
      <template v-else-if="upload.state === 'rejected'">
        <p>{{ upload.rejection.message }} The first findings, rejects first:</p>
        <table class="upload__findings">
          <thead>
            <tr><th>Severity</th><th>Code</th><th>Sheet</th><th class="num">Row</th><th>Finding</th></tr>
          </thead>
          <tbody>
            <tr v-for="(f, i) in rejectsFirst" :key="i">
              <td>{{ f.severity }}</td>
              <td>{{ f.code }}</td>
              <td>{{ f.sheet ?? '' }}</td>
              <td class="num">{{ f.row ?? '' }}</td>
              <td>{{ f.message }}</td>
            </tr>
          </tbody>
        </table>
      </template>
      <p v-else>{{ upload.name }} could not be added. {{ upload.message }}</p>
    </section>

    <p v-if="error" class="gbdi-card" role="alert">The buildings could not be loaded. {{ error }}</p>
    <p v-else-if="buildings === null" class="u-text-muted">Loading the buildings…</p>
    <p v-else-if="buildings.length === 0" class="gbdi-card">
      No building yet. Add an OpenBDF workbook to start; the list fills as workbooks are read.
    </p>

    <section v-else class="portfolio">
      <ul class="portfolio__legend">
        <li v-for="(stage, i) in STAGES" :key="stage.key">
          <span class="portfolio__swatch" :style="{ background: STAGE_COLORS[i] }" />{{ stage.label }}
        </li>
        <li><span class="portfolio__swatch portfolio__swatch--net" />Whole life, the net of the stages</li>
      </ul>
      <table class="portfolio__table">
        <thead>
          <tr>
            <th scope="col">Compare</th>
            <th scope="col">Building</th>
            <th scope="col" class="num">m² gross</th>
            <th scope="col">kg CO₂e per m², by life-cycle stage</th>
            <th scope="col" class="num">Whole life</th>
            <th scope="col">LETI band</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="b in sorted" :key="b.id" :class="{ 'portfolio__row--picked': picked.includes(b.id) }">
            <td>
              <q-checkbox
                v-model="picked"
                :val="b.id"
                dense
                :disable="picked.length >= 2 && !picked.includes(b.id)"
                :aria-label="`Compare ${code(b)}`"
              />
            </td>
            <td class="portfolio__building">
              <router-link class="portfolio__link" :to="`/buildings/${b.id}`">{{ code(b) }}</router-link>
              <span>{{ b.project_name ?? 'Unnamed project' }}</span>
              <span class="u-text-muted">{{ b.country ?? 'Country not declared' }}</span>
            </td>
            <td class="num">{{ figure(b.gross_floor_area_m2, kg) }}</td>
            <td class="portfolio__plot" aria-hidden="true">
              <template v-if="b.stages_per_m2">
                <span
                  v-for="seg in segments(b.stages_per_m2)"
                  :key="seg.key"
                  class="portfolio__seg"
                  :style="{ left: `${seg.left}%`, width: `${seg.width}%`, background: seg.color }"
                />
                <span class="portfolio__zero" :style="{ left: `${at(0)}%` }" />
                <span
                  v-if="b.whole_life_per_m2 !== null"
                  class="portfolio__net"
                  :style="{ left: `${at(b.whole_life_per_m2)}%` }"
                />
              </template>
            </td>
            <td class="num portfolio__figure">{{ figure(b.whole_life_per_m2, kg) }}</td>
            <td>{{ b.leti_band ?? 'not placed' }}</td>
          </tr>
        </tbody>
      </table>
      <p class="portfolio__caption">
        Bars left of zero are negative: most often biogenic carbon stored in timber at A1–A3 and released at end of
        life. Sorted by whole-life carbon per m². Pick two buildings to compare them.
      </p>
    </section>

    <div v-if="picked.length > 0" class="compare-bar">
      <p v-if="picked.length === 1">Pick one more building to compare with {{ codeOf(picked[0]) }}.</p>
      <q-btn
        v-else
        unelevated
        no-caps
        color="primary"
        :label="`Compare ${codeOf(picked[0])} with ${codeOf(picked[1])}`"
        :to="{ path: '/buildings/compare', query: { a: picked[0], b: picked[1] } }"
      />
      <q-btn flat no-caps label="Clear" @click="picked = []" />
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { ApiError } from '@/api/client';
import { code, fetchBuildings, uploadBuilding, type BuildingSummary, type Rejection } from '@/api/buildings';
import { STAGE_COLORS } from '@/dataviz';
import { figure, kg } from '@/format';

const STAGES = [
  { key: 'a1_a3', label: 'A1–A3' },
  { key: 'a4_a5', label: 'A4–A5' },
  { key: 'b1_b8', label: 'B1–B8' },
  { key: 'c1_c4', label: 'C1–C4' },
];

type Upload =
  | { state: 'reading'; name: string }
  | { state: 'added'; name: string; building: BuildingSummary }
  | { state: 'rejected'; name: string; rejection: Rejection }
  | { state: 'failed'; name: string; message: string };

const buildings = ref<BuildingSummary[] | null>(null);
const error = ref<string | null>(null);
const picked = ref<number[]>([]);
const upload = ref<Upload | null>(null);
const picker = ref<HTMLInputElement | null>(null);

async function load() {
  try {
    buildings.value = await fetchBuildings();
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e);
  }
}
onMounted(load);

async function onPick(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = '';
  if (!file) return;
  upload.value = { state: 'reading', name: file.name };
  try {
    const building = await uploadBuilding(file);
    upload.value = { state: 'added', name: code(building), building };
    await load();
  } catch (e: unknown) {
    if (e instanceof ApiError && e.status === 422) {
      upload.value = { state: 'rejected', name: file.name, rejection: e.body as Rejection };
    } else {
      upload.value = { state: 'failed', name: file.name, message: e instanceof Error ? e.message : String(e) };
    }
  }
}

const rejectsFirst = computed(() => {
  if (upload.value?.state !== 'rejected') return [];
  const findings = upload.value.rejection.findings;
  return [...findings.filter((f) => f.severity === 'Reject'), ...findings.filter((f) => f.severity !== 'Reject')].slice(0, 12);
});

const sorted = computed(() =>
  [...(buildings.value ?? [])].sort(
    (x, y) => (x.whole_life_per_m2 ?? Infinity) - (y.whole_life_per_m2 ?? Infinity),
  ),
);
const codeOf = (id: number) => {
  const b = buildings.value?.find((x) => x.id === id);
  return b ? code(b) : String(id);
};

// Chart geometry only: one scale for every row, from the most negative stack to the
// most positive one, so rows compare at a glance.
const extent = computed(() => {
  let lo = 0;
  let hi = 0;
  for (const b of buildings.value ?? []) {
    const values = Object.values(b.stages_per_m2 ?? {});
    lo = Math.min(lo, values.filter((v) => v < 0).reduce((s, v) => s + v, 0));
    hi = Math.max(hi, values.filter((v) => v > 0).reduce((s, v) => s + v, 0));
  }
  return { lo, hi };
});
const at = (value: number) => {
  const { lo, hi } = extent.value;
  return hi === lo ? 0 : ((value - lo) / (hi - lo)) * 100;
};
function segments(stages: Record<string, number>) {
  let up = 0;
  let down = 0;
  return STAGES.map((stage, i) => {
    const v = stages[stage.key] ?? 0;
    const from = v >= 0 ? up : down + v;
    if (v >= 0) up += v;
    else down += v;
    return { key: stage.key, color: STAGE_COLORS[i], left: at(from), width: at(from + Math.abs(v)) - at(from) };
  });
}
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.buildings__head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-end;
  gap: tokens.$spacing-xl;
}

.buildings__head p {
  margin-bottom: 0;
}

.upload {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-md;
}

.upload p {
  margin: 0;
}

.upload__findings {
  border-collapse: collapse;
  font-size: tokens.$text-size-sm;
}

.upload__findings th,
.upload__findings td {
  padding: tokens.$spacing-xxs tokens.$spacing-md tokens.$spacing-xxs 0;
  text-align: left;
  vertical-align: top;
}

.portfolio {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-md;
}

.portfolio__legend {
  display: flex;
  flex-wrap: wrap;
  gap: tokens.$spacing-lg;
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: tokens.$text-size-sm;
}

.portfolio__swatch {
  display: inline-block;
  width: 0.75rem;
  height: 0.75rem;
  margin-right: tokens.$spacing-xs;
  vertical-align: -0.1rem;
}

.portfolio__swatch--net {
  width: 3px;
  height: 1rem;
  background: tokens.$color-text;
}

.portfolio__table {
  width: 100%;
  border-collapse: collapse;
  font-variant-numeric: tabular-nums;
}

.portfolio__table th {
  padding: tokens.$spacing-sm;
  font-size: tokens.$text-size-xs;
  font-weight: tokens.$text-weight-regular;
  color: tokens.$color-text-muted;
  text-align: left;
  border-bottom: tokens.$border-width solid tokens.$color-border;
}

.portfolio__table td {
  padding: tokens.$spacing-sm;
  border-bottom: tokens.$border-width solid tokens.$color-border;
  vertical-align: middle;
}

.portfolio__row--picked {
  background: tokens.$color-surface-muted;
}

.portfolio__building {
  display: flex;
  flex-direction: column;
  font-size: tokens.$text-size-sm;
}

.portfolio__link {
  font-weight: tokens.$text-weight-bold;
  font-size: tokens.$text-size-base;
  color: tokens.$color-primary-strong;
  text-decoration: none;
}

.portfolio__link:hover,
.portfolio__link:focus-visible {
  text-decoration: underline;
}

.portfolio__plot {
  position: relative;
  width: 45%;
  height: 3rem;
}

.portfolio__seg {
  position: absolute;
  top: calc(50% - 0.6rem);
  height: 1.2rem;
}

.portfolio__zero {
  position: absolute;
  top: tokens.$spacing-xs;
  bottom: tokens.$spacing-xs;
  border-left: tokens.$border-width solid tokens.$color-text-muted;
}

.portfolio__net {
  position: absolute;
  top: calc(50% - 0.9rem);
  width: 3px;
  height: 1.8rem;
  margin-left: -1px;
  background: tokens.$color-text;
}

.portfolio__figure {
  font-size: tokens.$text-size-lg;
  font-weight: tokens.$text-weight-bold;
}

.num {
  text-align: right;
  white-space: nowrap;
}

.portfolio__caption {
  margin: 0;
  max-width: 42rem;
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}

.compare-bar {
  position: sticky;
  bottom: tokens.$spacing-lg;
  display: flex;
  align-items: center;
  gap: tokens.$spacing-md;
  justify-self: start;
  padding: tokens.$spacing-md tokens.$spacing-lg;
  border: tokens.$border-width solid tokens.$color-border;
  border-radius: tokens.$radius-card;
  background: tokens.$color-surface;
}

.compare-bar p {
  margin: 0;
}
</style>
