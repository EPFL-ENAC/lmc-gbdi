<template>
  <!-- The building as the materials it is made of: a material passport's mass composition
       (as in Madaster), then one data sheet per material, laid out the way an FDES or EPD
       presents a product (as in INIES). Two panels of the Overview sheet. -->
  <!-- The same ten materials in two walls, by mass and by carbon, one colour each:
       heavy is not the same as intense. The switch picks which ranking sets the ten, for
       the walls, the stage matrix and the cards; it sticks while the materials are on screen. -->
  <div class="passport">
    <div class="passport__bar">
      <span id="passport-rank">Top 10 materials</span>
      <q-btn-toggle
        v-model="rankBy"
        :options="RANKINGS"
        aria-labelledby="passport-rank"
        dense
        no-caps
        unelevated
        toggle-color="primary"
        color="white"
        text-color="dark"
        class="passport__switch"
      />
    </div>
    <section class="sheet__panel passport__section">
      <h2 class="sheet__panel-title">What it weighs, what it emits</h2>
      <p class="u-text-muted">
        {{ rankBy === 'mass' ? 'The ten heaviest materials, and the carbon each carries.' : 'The ten materials with the most carbon, and what each weighs.' }}
        One colour per material in both walls; one brick is one per cent.
      </p>
      <p class="passport__cover">
        Together, these ten make {{ percent.format(cover.carbon) }} of the total carbon and
        {{ percent.format(cover.mass) }} of the mass.
      </p>
      <div class="grid-2-col passport__walls">
        <figure class="passport__wall">
          <figcaption>Mass, {{ num.format(overview.total_mass_kg) }} {{ overview.units.mass }}</figcaption>
          <BrickWall :parts="ranked.map((r) => ({ color: r.color, label: r.label, share: r.share_of_mass ?? 0 }))" label="Mass by material" />
        </figure>
        <figure class="passport__wall">
          <figcaption>Carbon ({{ overview.headline.scope }}), {{ num.format(overview.headline.whole_life) }} {{ overview.units.carbon }}</figcaption>
          <BrickWall :parts="ranked.map((r) => ({ color: r.color, label: r.label, share: r.share }))" label="Carbon by material" />
        </figure>
      </div>
      <table class="passport__legend">
        <thead>
          <tr>
            <th scope="col">Material</th>
            <th scope="col" class="num">{{ overview.units.mass }}</th>
            <th scope="col" class="num">Share of the mass</th>
            <th scope="col" class="num">{{ overview.units.carbon }}</th>
            <th scope="col" class="num">Share of the carbon</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in ranked" :key="row.key">
            <th scope="row">
              <span class="passport__swatch" :style="{ background: row.color }" /><Term :name="row.label" />
              <span class="passport__product">{{ row.epd_product }}</span>
            </th>
            <td class="num">{{ num.format(row.mass_kg) }}</td>
            <td class="num">{{ row.share_of_mass === null ? 'no mass declared' : percent.format(row.share_of_mass) }}</td>
            <td class="num">{{ num.format(row.gwp) }}</td>
            <td class="num">{{ percent.format(row.share) }}</td>
          </tr>
          <tr>
            <th scope="row"><span class="passport__swatch" :style="{ background: OTHER_COLOR }" />Every other material</th>
            <td colspan="4" class="num"><ShowMore v-model="open" :count="rest.length" /></td>
          </tr>
          <template v-if="open">
            <tr v-for="row in rest" :key="row.key" class="passport__rest">
              <th scope="row">
                <span class="passport__swatch" :style="{ background: OTHER_COLOR }" /><Term :name="row.label" />
                <span class="passport__product">{{ row.epd_product }}</span>
              </th>
              <td class="num">{{ num.format(row.mass_kg) }}</td>
              <td class="num">{{ row.share_of_mass === null ? 'no mass declared' : percent.format(row.share_of_mass) }}</td>
              <td class="num">{{ num.format(row.gwp) }}</td>
              <td class="num">{{ percent.format(row.share) }}</td>
            </tr>
          </template>
        </tbody>
      </table>
    </section>

    <section class="sheet__panel passport__section">
      <h2 class="sheet__panel-title">Material by stage</h2>
      <p class="u-text-muted">{{ rankBy === 'mass' ? 'The ten heaviest materials' : 'The ten materials with the most carbon' }}, stage by stage.</p>
      <StageMatrix
        :stages="overview.stages"
        :rows="ranked.map((r, i) => ({ key: r.key, label: r.label, gwp_by_stage: top[i].gwp_by_stage, color: r.color }))"
        :units="overview.units"
        row-header="Material"
        empty-label="No materials in this project."
      />
    </section>

    <section class="sheet__panel passport__section">
      <h2 class="sheet__panel-title">Material by material</h2>
      <p class="u-text-muted">
        {{ rankBy === 'mass' ? 'The ten heaviest materials.' : 'The ten materials with the most carbon.' }}
        Heavy is not the same as intense: compare the mass with the carbon per kg. The bars of every
        card share one scale, set by these ten.
      </p>
      <div class="grid-2-col">
        <MaterialSheet
          v-for="(hotspot, i) in top"
          :key="pairKey(hotspot)"
          :hotspot="hotspot"
          :color="MATERIAL_COLORS[i]"
          :stages="overview.stages"
          :units="overview.units"
          :rank="i + 1"
          :domain="stageDomain"
        />
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import BrickWall from '@/components/BrickWall.vue';
import MaterialSheet from '@/components/MaterialSheet.vue';
import StageMatrix from '@/components/StageMatrix.vue';
import ShowMore from '@/components/atoms/ShowMore.vue';
import Term from '@/components/atoms/Term.vue';
import type { Overview } from '@/api/overview';
import { MATERIAL_COLORS, OTHER_COLOR } from '@/dataviz';
import { amount, percent } from '@/format';
import { materialLabel, pairKey, RANKINGS, remaining, type RankBy } from '@/materials';

const props = defineProps<{ overview: Overview }>();
const num = computed(() => amount(props.overview.units));

const rankBy = ref<RankBy>('mass');

// The ten of the chosen ranking, as the backend sends them. All three panels read it.
const top = computed(() => (rankBy.value === 'mass' ? props.overview.mass_hotspots : props.overview.material_hotspots));

// One row per material of the ranking, both measures from the backend; the colour
// follows the rank, so a material has the same one in the walls, the matrix and the cards.
const ranked = computed(() =>
  top.value.map((h, i) => ({
    key: pairKey(h),
    label: materialLabel(h),
    epd_product: h.material ? h.epd_product : '',
    mass_kg: h.mass_kg,
    share_of_mass: h.share_of_mass,
    gwp: h.gwp,
    share: h.share,
    color: MATERIAL_COLORS[i],
  })),
);

// ponytail: the ten backend shares summed here, as the payload has no such total;
// move it into the overview when a backend PR next touches it.
const cover = computed(() => ({
  carbon: ranked.value.reduce((sum, r) => sum + r.share, 0),
  mass: ranked.value.reduce((sum, r) => sum + (r.share_of_mass ?? 0), 0),
}));

// Bar geometry only: the lowest and highest stage of the ten shown, zero inside, one scale for every card.
const stageDomain = computed(() => {
  const values = top.value.flatMap((h) => Object.values(h.gwp_by_stage));
  return [Math.min(0, ...values), Math.max(0, ...values)] as const;
});

// The materials the wall paints as "every other", in the same ranking.
const open = ref(false);
const rest = computed(() => {
  return remaining(props.overview.materials, top.value, rankBy.value).map((m) => ({
    key: pairKey(m),
    label: materialLabel(m),
    epd_product: m.material ? m.epd_product : '',
    mass_kg: m.mass_kg,
    share_of_mass: m.share_of_mass,
    gwp: m.gwp,
    share: m.share,
  }));
});
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.passport__section p {
  margin: 0;
}

.passport__cover {
  font-size: tokens.$text-size-lg;
}

// The panels sit in one wrapper, so the sheet's rule between panels is drawn here again.
.passport > .sheet__panel + .sheet__panel {
  border-top: tokens.$border-width solid tokens.$color-border-control;
}

// Sticks under the page header (SheetToc keeps --sheet-header-h at its height) and
// leaves with the wrapper, at the end of the materials part.
.passport__bar {
  position: sticky;
  top: var(--sheet-header-h);
  z-index: tokens.$z-index-sticky;
  display: flex;
  flex-wrap: nowrap;
  align-items: center;
  gap: tokens.$spacing-md;
  padding: tokens.$spacing-sm tokens.$spacing-xl;
  border-bottom: tokens.$border-width solid tokens.$color-border-control;
  background: tokens.$color-surface;
  font-size: tokens.$text-size-sm;
  white-space: nowrap;
}

.passport__switch {
  border: tokens.$border-width solid tokens.$color-border;
}

.passport__walls {
  column-gap: tokens.$spacing-page;
}

.passport__wall {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-sm;
  margin: 0;
  font-size: tokens.$text-size-sm;
}

.passport__legend {
  width: 100%;
  border-collapse: collapse;
  font-size: tokens.$text-size-sm;
  font-variant-numeric: tabular-nums;
}

.passport__legend th,
.passport__legend td {
  padding: tokens.$spacing-xs tokens.$spacing-sm;
  border-bottom: tokens.$border-width solid tokens.$color-border;
  text-align: left;
  font-weight: tokens.$text-weight-regular;
}

.passport__legend thead th {
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}

.passport__legend .num {
  text-align: right;
  white-space: nowrap;
}

.passport__swatch {
  display: inline-block;
  width: tokens.$spacing-lg;
  height: tokens.$spacing-sm;
  margin-right: tokens.$spacing-sm;
  border-radius: tokens.$radius-xs;
}

.passport__product {
  display: block;
  padding-left: calc(#{tokens.$spacing-lg} + #{tokens.$spacing-sm});
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}
</style>
