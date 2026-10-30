<template>
  <!-- Variant 5, "Time": the whole life as it happens. Whole-life carbon studies plot
       carbon over the study period; the upfront share is the part already spent the
       day the building opens, which is why it matters most now. -->
  <q-page class="page-grid">
    <p v-if="error" class="gbdi-card" role="alert">The project could not be loaded. {{ error }}</p>
    <p v-else-if="overview === null" class="u-text-muted">Loading the project…</p>

    <template v-else>
      <header>
        <p class="time__name">{{ overview.project.project_name ?? 'Unnamed project' }}</p>
        <h1 class="time__statement">
          {{ percent.format(overview.headline.upfront_share) }} of its whole-life carbon is emitted
          <span class="text-display-lead">before anyone moves in.</span>
        </h1>
      </header>

      <section class="time__chart">
        <CarbonOverTime
          v-if="overview.use_per_year !== null && overview.project.reference_study_period_years !== null"
          :upfront="overview.headline.upfront"
          :use-total="stageGwp('b1_b8')"
          :use-per-year="overview.use_per_year"
          :end-of-life="stageGwp('c1_c4')"
          :whole-life="overview.headline.whole_life"
          :module-d="overview.headline.module_d1"
          :period="overview.project.reference_study_period_years"
        />
        <p v-else class="u-text-muted">
          The study period is not declared, so the years of use cannot be drawn.
        </p>
      </section>

      <!-- The life cycle is a sequence, so its moments are numbered by when they happen. -->
      <section class="time__moments" aria-label="The four moments of the life cycle">
        <article class="time__moment">
          <p class="time__when">Year 0</p>
          <p class="time__figure">{{ kg.format(overview.headline.upfront) }}</p>
          <p class="time__what">kg CO₂e to make the materials and build (A1–A5).</p>
        </article>
        <article class="time__moment">
          <p class="time__when">Years 1 to {{ overview.project.reference_study_period_years }}</p>
          <p class="time__figure">{{ figure(overview.use_per_year, kg) }}</p>
          <p class="time__what">kg CO₂e a year on average to maintain, repair and replace (B1–B8).</p>
        </article>
        <article class="time__moment">
          <p class="time__when">Year {{ overview.project.reference_study_period_years }}</p>
          <p class="time__figure">{{ kg.format(stageGwp('c1_c4')) }}</p>
          <p class="time__what">kg CO₂e to take the building down and process the waste (C1–C4).</p>
        </article>
        <article class="time__moment time__moment--beyond">
          <p class="time__when">Beyond</p>
          <p class="time__figure">{{ kg.format(overview.headline.module_d1) }}</p>
          <p class="time__what">kg CO₂e of benefits from reuse and recycling (D1), outside the total.</p>
        </article>
      </section>

      <section class="time__section">
        <h2 class="time__title">Which elements carry the end of life</h2>
        <p class="u-text-muted">
          The step at year {{ overview.project.reference_study_period_years }} comes from the elements whose C1–C4
          dominates. The shade marks each cell against the largest.
        </p>
        <StageMatrix :stages="overview.stages" :rows="overview.element_stages" />
      </section>
    </template>
  </q-page>
</template>

<script setup lang="ts">
import CarbonOverTime from '@/components/CarbonOverTime.vue';
import StageMatrix from '@/components/StageMatrix.vue';
import { useOverview } from '@/composables/useOverview';
import { figure, kg, percent } from '@/format';

const { overview, error } = useOverview();

const stageGwp = (key: string) => overview.value?.stages.find((s) => s.key === key)?.gwp ?? 0;
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

.time__chart {
  padding: tokens.$spacing-xl;
  border: tokens.$border-width solid tokens.$color-border;
  border-radius: tokens.$radius-panel;
}

.time__moments {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  border-top: tokens.$border-width solid tokens.$color-border;
}

.time__moment {
  padding: tokens.$spacing-lg tokens.$spacing-xl tokens.$spacing-lg 0;
}

.time__moment p {
  margin: 0;
}

.time__moment + .time__moment {
  padding-left: tokens.$spacing-xl;
  border-left: tokens.$border-width solid tokens.$color-border;
}

.time__when {
  font-size: tokens.$text-size-sm;
  color: tokens.$color-text-muted;
}

.time__figure {
  font-family: tokens.$text-font-family-display;
  font-size: tokens.$text-size-display-md;
  line-height: tokens.$text-line-height-tight;
  font-variant-numeric: tabular-nums;
}

.time__moment--beyond .time__figure {
  color: tokens.$color-text-muted;
}

.time__what {
  max-width: 16rem;
  font-size: tokens.$text-size-sm;
}

.time__section {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-md;
}

.time__section p {
  margin: 0;
}

.time__title {
  margin: 0;
  font-family: tokens.$text-font-family;
  font-size: tokens.$text-size-heading-lg;
}

@media (max-width: 1199px) {
  .time__moments {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
