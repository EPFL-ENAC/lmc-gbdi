<template>
  <!-- A draft whose rejects block carbon: why, then what still reads. No figure is
       shown that the rejects make wrong; the materials by mass hold unless blocked too. -->
  <q-page class="page-grid">
    <p v-if="error" class="gbdi-card" role="alert">The draft could not be loaded. {{ error }}</p>
    <p v-else-if="draft === null" class="u-text-muted">Loading the draft…</p>

    <template v-else>
      <header>
        <h1>
          {{ name }}<br />
          <span class="text-display-lead">Draft, no carbon figures</span>
        </h1>
        <p class="text-lead">
          Stored despite the rejects below. Until the workbook is fixed and added again, its carbon is not shown,
          counted or compared.
        </p>
      </header>

      <section class="draft__section">
        <h2 class="draft__title">Why it is a draft</h2>
        <ul class="draft__rejects">
          <li v-for="(f, i) in draft.rejects" :key="i">
            <strong>{{ f.code }}</strong>, {{ f.sheet ?? 'workbook' }}: {{ f.message }}
          </li>
        </ul>
      </section>

      <section v-if="!draft.blocked.includes('materials')" class="draft__section">
        <h2 class="draft__title">What it is made of, by mass</h2>
        <p class="u-text-muted">
          {{ kg.format(draft.total_mass_kg ?? 0) }} kg in all<template v-if="draft.gross_floor_area_m2">,
            {{ kg.format((draft.total_mass_kg ?? 0) / draft.gross_floor_area_m2) }} kg per m² of gross floor area</template
          >, from {{ kg.format(draft.rows_read) }} bill of materials lines. The bill of materials holds; only its
          results do not.
        </p>
        <RankedBars :bars="massBars" caption="kg, by OpenBDF material class." empty-label="No materials." />
      </section>

      <section class="draft__section">
        <h2 class="draft__title">Project</h2>
        <ProjectFieldsTable :fields="draft.project_fields" />
      </section>
    </template>
  </q-page>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { fetchDraft, type DraftView } from '@/api/buildings';
import ProjectFieldsTable from '@/components/ProjectFieldsTable.vue';
import RankedBars, { type Bar } from '@/components/RankedBars.vue';
import { kg } from '@/format';

const props = defineProps<{ id: number }>();
const draft = ref<DraftView | null>(null);
const error = ref<string | null>(null);

watch(
  () => props.id,
  async (id) => {
    draft.value = null;
    error.value = null;
    try {
      draft.value = await fetchDraft(id);
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e);
    }
  },
  { immediate: true },
);

const name = computed(
  () => draft.value?.project_fields.find((f) => f.code === 'project_name')?.value ?? 'Unnamed project',
);
const massBars = computed<Bar[]>(() =>
  [...(draft.value?.material_classes ?? [])]
    .sort((x, y) => y.mass_kg - x.mass_kg)
    .map((c) => ({ key: c.label, label: c.label, value: c.mass_kg, display: kg.format(c.mass_kg) })),
);
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.draft__section {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-md;
  padding-top: tokens.$spacing-xl;
  border-top: tokens.$border-width solid tokens.$color-border;
}

.draft__section > p {
  margin: 0;
}

.draft__title {
  margin: 0;
  font-family: tokens.$text-font-family;
  font-size: tokens.$text-size-heading-lg;
}

.draft__rejects {
  margin: 0;
  padding-left: tokens.$spacing-lg;
}
</style>
