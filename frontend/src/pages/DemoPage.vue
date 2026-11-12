<template>
  <q-page class="page-grid">
    <!-- One statement, two tones: the second half fades to Grey Text (p.35) -->
    <section>
      <h1>Open Data<br /><span class="text-display-lead">Better Buildings</span></h1>
      <p class="text-lead">
        Design resilient buildings with better climate performance. Manage your portfolio's footprint.
        Develop effective climate policy. Use our data and tools to assess and reduce resource use and
        embodied carbon emissions.
      </p>
      <div class="demo-actions">
        <q-btn unelevated no-caps color="primary" label="Explore the data" to="/buildings" />
        <!-- ponytail: the parser is the methodology until a written one exists. -->
        <q-btn
          unelevated
          no-caps
          class="btn-secondary"
          label="Read the methodology"
          href="https://github.com/EPFL-ENAC/lmc-openbdf"
          target="_blank"
          rel="noopener"
        />
      </div>
    </section>

    <!-- The one set of hero cards on the page: the buildings in the database, now. -->
    <p v-if="error" class="gbdi-card" role="alert">The buildings could not be loaded. {{ error }}</p>
    <p v-else-if="heroes === null" class="u-text-muted">Counting the buildings…</p>
    <p v-else-if="heroes.length === 0" class="gbdi-card">
      No building is loaded yet. <router-link class="link" to="/buildings">Add a COLA workbook</router-link>.
    </p>
    <section v-else class="grid-3-col" aria-label="Key figures">
      <BigNumber v-for="hero in heroes" :key="hero.tone" :value="hero.number" :tone="hero.tone" :to="hero.to">
        {{ hero.text }}<sup>1</sup>
      </BigNumber>
    </section>
    <p v-if="coverage" class="u-text-muted demo-coverage">{{ coverage }}</p>

    <section class="grid-3-col">
      <article class="gbdi-card">
        <svg class="gbdi-card__illustration gbdi-illustration" viewBox="0 0 120 120" width="120" height="120" aria-hidden="true">
          <circle cx="60" cy="60" r="48" />
          <ellipse cx="60" cy="60" rx="32" ry="48" />
          <ellipse cx="60" cy="60" rx="14" ry="48" />
          <path d="M60 12v96" />
          <circle class="accent" cx="38" cy="36" r="4" />
          <circle class="accent" cx="74" cy="52" r="4" />
          <circle class="accent" cx="50" cy="78" r="4" />
          <circle class="accent" cx="88" cy="72" r="4" />
        </svg>
        <h2 class="gbdi-card__title">Better data</h2>
        <p class="gbdi-card__body">
          Open, comparable building and whole-life carbon data, collected with one global methodology.
        </p>
      </article>
      <article class="gbdi-card">
        <svg class="gbdi-card__illustration gbdi-illustration" viewBox="0 0 120 120" width="120" height="120" aria-hidden="true">
          <path d="M14 58l52-28 40 22-52 28z" />
          <path d="M14 58v24l40 22V80" />
          <path d="M54 104l52-28V52" />
          <path class="accent" d="M40 54l10-5 8 4-10 5z" />
          <path class="accent" d="M60 49l10-5 8 4-10 5z" />
        </svg>
        <h2 class="gbdi-card__title">Better materials</h2>
        <p class="gbdi-card__body">
          Material hotspots that show where a low-carbon alternative changes the result most.
        </p>
      </article>
      <article class="gbdi-card">
        <svg class="gbdi-card__illustration gbdi-illustration" viewBox="0 0 120 120" width="120" height="120" aria-hidden="true">
          <path class="accent" d="M34 30l26-14 26 14-26 14z" />
          <path d="M34 30v58l26 14V44" />
          <path d="M60 102l26-14V30" />
          <path d="M64 52l18-10M64 64l18-10M64 76l18-10M64 88l18-10" />
        </svg>
        <h2 class="gbdi-card__title">Better design</h2>
        <p class="gbdi-card__body">
          Benchmarks that let a design team compare an option against real buildings, early enough to
          matter.
        </p>
      </article>
    </section>

    <footer class="u-text-muted">
      <ol>
        <li>
          Live from the GBDI database: whole-life carbon per m² of gross floor area, over the modules each COLA
          workbook declares.
        </li>
      </ol>
    </footer>
  </q-page>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { code, fetchBuildings, type BuildingSummary } from '@/api/buildings';
import { buildingPath } from '@/buildingLayouts';
import BigNumber from '@/components/molecules/BigNumber.vue';
import { kg } from '@/format';

const buildings = ref<BuildingSummary[] | null>(null);
const error = ref<string | null>(null);
const drafts = ref(0);

onMounted(async () => {
  try {
    // A draft is visible in the list but never counted here.
    const all = await fetchBuildings();
    buildings.value = all.filter((b) => !b.draft);
    drafts.value = all.length - buildings.value.length;
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e);
  }
});

// What the figures cannot show yet: the declarations most workbooks leave blank.
const coverage = computed(() => {
  const all = buildings.value;
  if (!all?.length) return '';
  const count = (has: (b: BuildingSummary) => boolean) => `${all.filter(has).length} of ${all.length}`;
  return (
    `Declared so far: a gross floor area in ${count((b) => b.gross_floor_area_m2 !== null)} buildings, ` +
    `a useful floor area in ${count((b) => b.useful_floor_area_m2 !== null)}, ` +
    `a study period in ${count((b) => b.study_period_years !== null)}. ` +
    'Without them a building is left out of per-m² figures and the years of use.'
  );
});

const median = (values: number[]) => {
  const s = [...values].sort((x, y) => x - y);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid]! : (s[mid - 1]! + s[mid]!) / 2;
};

// Three figures from the stored buildings; null while loading, [] when there are none.
const heroes = computed(() => {
  const all = buildings.value;
  if (all === null) return null;
  if (all.length === 0) return [];
  const countries = new Set(all.map((b) => b.country).filter(Boolean)).size;
  const rows = all.reduce((sum, b) => sum + b.rows_read, 0);
  const rated = all.filter((b) => b.whole_life_per_m2 !== null).sort((x, y) => x.whole_life_per_m2! - y.whole_life_per_m2!);
  const heroes = [
    {
      tone: 'green' as const,
      number: kg.format(all.length),
      text:
        `buildings from ${countries} ${countries === 1 ? 'country' : 'countries'}, ${kg.format(rows)} bill-of-materials lines read` +
        (drafts.value ? `; ${drafts.value} drafts not counted.` : '.'),
      to: '/buildings',
    },
  ];
  if (rated.length === 0) return heroes;
  const low = rated[0]!;
  const high = rated[rated.length - 1]!;
  return [
    ...heroes,
    {
      tone: 'blue' as const,
      number: kg.format(median(rated.map((b) => b.whole_life_per_m2!))),
      text: 'kg CO₂e per m², the median building over its whole life.',
      to: '/buildings',
    },
    {
      tone: 'purple' as const,
      number: `${kg.format(low.whole_life_per_m2!)}–${kg.format(high.whole_life_per_m2!)}`,
      text: `kg CO₂e per m², from ${code(low)} to ${code(high)}. Compare the two.`,
      to: buildingPath(low.id, high.id),
    },
  ];
});
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;


.demo-coverage {
  margin: 0;
  font-size: tokens.$text-size-sm;
}

.demo-actions {
  display: flex;
  flex-wrap: wrap;
  gap: tokens.$spacing-sm;
}
</style>
