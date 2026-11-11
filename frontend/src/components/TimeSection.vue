<template>
  <!-- The whole life as it happens. Whole-life carbon studies plot carbon over the study
       period; the upfront share is the part already spent the day the building opens,
       which is why it matters most now. -->
  <div class="time">
    <p v-if="period === null" class="time__warning" role="note">
      The workbook declares no study period, so the years of use are not drawn and the use
      figures stand without a time scale. Declare it in General Information and add the
      workbook again.
    </p>
    <h2 class="time__statement">
      {{ percent.format(overview.headline.upfront_share) }} of its whole-life carbon is emitted
      <span class="text-display-lead">before anyone moves in.</span>
    </h2>

    <div v-if="period !== null && overview.use_per_year !== null" class="time__chart">
      <CarbonOverTime
        :stages="overview.stages"
        :use-per-year="overview.use_per_year"
        :module-d="overview.headline.module_d1"
        :period="period"
      />
    </div>

    <!-- The life cycle is a sequence, so its moments are numbered by when they happen. -->
    <div class="time__moments" role="group" aria-label="The four moments of the life cycle">
      <article class="time__moment">
        <p class="time__when">Year 0</p>
        <p class="time__figure">{{ kg.format(overview.headline.upfront) }}</p>
        <p class="time__what">kg CO₂e to make the materials and build (A1–A5).</p>
      </article>
      <article class="time__moment">
        <p class="time__when">{{ period === null ? 'Years of use' : `Years 1 to ${period}` }}</p>
        <p class="time__figure">{{ figure(overview.use_per_year, kg) }}</p>
        <p class="time__what">kg CO₂e a year on average to maintain, repair and replace (B1–B8).</p>
      </article>
      <article class="time__moment">
        <p class="time__when">{{ period === null ? 'End of life' : `Year ${period}` }}</p>
        <p class="time__figure">{{ kg.format(stageGwp('c1_c4')) }}</p>
        <p class="time__what">kg CO₂e to take the building down and process the waste (C1–C4).</p>
      </article>
      <article class="time__moment time__moment--beyond">
        <p class="time__when">Beyond</p>
        <p class="time__figure">{{ kg.format(overview.headline.module_d1) }}</p>
        <p class="time__what">kg CO₂e of benefits from reuse and recycling (D1), outside the total.</p>
      </article>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { Overview } from '@/api/overview';
import CarbonOverTime from '@/components/CarbonOverTime.vue';
import { figure, kg, percent } from '@/format';

const props = defineProps<{ overview: Overview }>();

const period = computed(() => props.overview.project.reference_study_period_years);
const stageGwp = (key: string) => props.overview.stages.find((s) => s.key === key)?.gwp ?? 0;
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.time {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-lg;
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

.time__warning {
  margin: 0;
  padding: tokens.$spacing-sm tokens.$spacing-lg;
  background: tokens.$color-surface-highlight;
  font-size: tokens.$text-size-sm;
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

@media (max-width: 1199px) {
  .time__moments {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
