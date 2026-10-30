<template>
  <!-- Variant 4, "Benchmark": where the project stands on published scales, the way
       building LCA tools place a design against a regulation or a rating. Every scale
       says what it counts, so the comparison stays honest. -->
  <q-page class="page-grid">
    <p v-if="error" class="gbdi-card" role="alert">The project could not be loaded. {{ error }}</p>
    <p v-else-if="overview === null" class="u-text-muted">Loading the project…</p>

    <template v-else>
      <header>
        <h1>
          {{ overview.project.project_name ?? 'Unnamed project' }}<br />
          <span class="text-display-lead">Against published scales</span>
        </h1>
        <p class="text-lead">
          Reference points, not a compliance check: each scale counts its own modules over its own floor area.
          Read the scope under each one before quoting a result.
        </p>
      </header>

      <section v-if="leti" class="bench">
        <div class="bench__aside">
          <h2 class="bench__title">{{ leti.name }}</h2>
          <p class="bench__verdict">
            Band <strong>{{ leti.band }}</strong> at {{ figure(leti.value, one) }} kg CO₂e per m² of gross floor area.
          </p>
          <p class="bench__scope">{{ leti.scope }}</p>
          <p class="bench__source">
            Source: <a class="link" :href="leti.source_url" target="_blank" rel="noopener">{{ leti.source }}</a>
          </p>
        </div>
        <RatingLabel :benchmark="leti" />
      </section>

      <section v-if="re2020" class="bench">
        <div class="bench__aside">
          <h2 class="bench__title">{{ re2020.name }}</h2>
          <p class="bench__verdict">{{ re2020.band }}, at {{ figure(re2020.value, one) }} kg CO₂e per m² of useful floor area.</p>
          <p class="bench__scope">{{ re2020.scope }}</p>
          <p class="bench__source">
            Source: <a class="link" :href="re2020.source_url" target="_blank" rel="noopener">{{ re2020.source }}</a>
          </p>
        </div>
        <CeilingRuler :benchmark="re2020" />
      </section>

      <section class="bench">
        <div class="bench__aside">
          <h2 class="bench__title">What would move it</h2>
          <p class="bench__scope">
            A band moves with the elements and materials that carry the most carbon. These are the levers.
          </p>
        </div>
        <div class="grid-2-col">
          <RankedBars :bars="elementBars" caption="Building elements, share of the whole life." empty-label="No classified elements." />
          <RankedBars :bars="materialBars" caption="Materials, share of the whole life." empty-label="No materials." />
        </div>
      </section>

      <section class="bench">
        <div class="bench__aside">
          <h2 class="bench__title">Is the scope complete?</h2>
          <p class="bench__scope">
            A rating is only as good as the modules behind it. A module declared without a result is either missing or reported inside another, as A1 is here inside A1–A3.
          </p>
        </div>
        <ModuleChecks
          :checks="overview.module_checks"
          :rows-read="overview.rows_read"
          :declared-without-result="overview.modules_declared_without_result"
          :result-without-declaration="overview.modules_with_undeclared_result"
        />
      </section>
    </template>
  </q-page>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import CeilingRuler from '@/components/CeilingRuler.vue';
import ModuleChecks from '@/components/ModuleChecks.vue';
import RankedBars, { type Bar } from '@/components/RankedBars.vue';
import RatingLabel from '@/components/RatingLabel.vue';
import { useOverview } from '@/composables/useOverview';
import { figure, one, percent } from '@/format';

const { overview, error } = useOverview();

const leti = computed(() => overview.value?.benchmarks.find((b) => b.key === 'leti'));
const re2020 = computed(() => overview.value?.benchmarks.find((b) => b.key === 're2020'));

const elementBars = computed<Bar[]>(() =>
  (overview.value?.elements ?? []).map((e) => ({
    key: e.element,
    label: e.element,
    value: e.share,
    display: percent.format(e.share),
  })),
);
const materialBars = computed<Bar[]>(() =>
  (overview.value?.material_hotspots ?? []).slice(0, 5).map((m) => ({
    key: `${m.material}|${m.epd_product}`,
    label: m.material || m.epd_product,
    value: m.share,
    display: percent.format(m.share),
  })),
);
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.bench {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 2fr);
  gap: tokens.$spacing-page;
  padding-top: tokens.$spacing-xl;
  border-top: tokens.$border-width solid tokens.$color-border;
}

.bench__aside {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-md;
}

.bench__aside p {
  margin: 0;
}

.bench__title {
  margin: 0;
  font-family: tokens.$text-font-family;
  font-size: tokens.$text-size-heading-lg;
}

.bench__verdict {
  font-size: tokens.$text-size-lg;
}

.bench__scope,
.bench__source {
  font-size: tokens.$text-size-sm;
  color: tokens.$color-text-muted;
}

@media (max-width: 1199px) {
  .bench {
    grid-template-columns: minmax(0, 1fr);
    gap: tokens.$spacing-xl;
  }
}
</style>
