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
        <h2 class="draft__title">Everything openbdf reported</h2>
        <p class="u-text-muted">
          {{ kg.format(draft.findings.length) }} findings, grouped by code, rejects first. Warnings do not block
          anything; they are what to tidy in the workbook.
        </p>
        <details v-for="group in groups" :key="group.key" class="draft__group">
          <summary>
            <strong>{{ group.code }}</strong> {{ group.severity }}, {{ group.sheet ?? 'workbook' }},
            {{ kg.format(group.items.length) }}×: {{ group.items[0]!.message }}
          </summary>
          <ol class="draft__findings">
            <li v-for="(f, i) in group.items" :key="i">
              <template v-if="f.row !== null">Row {{ f.row }}: </template>{{ f.message }}
            </li>
          </ol>
        </details>
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
import { fetchDraft, type DraftView, type Finding } from '@/api/buildings';
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
// Findings by code, severity and sheet, rejects first, then the most frequent.
const groups = computed(() => {
  const by = new Map<string, { key: string; code: string; severity: string; sheet: string | null; items: Finding[] }>();
  for (const f of draft.value?.findings ?? []) {
    const key = `${f.severity}|${f.code}|${f.sheet ?? ''}`;
    if (!by.has(key)) by.set(key, { key, code: f.code, severity: f.severity, sheet: f.sheet, items: [] });
    by.get(key)!.items.push(f);
  }
  const rank = (s: string) => (s === 'Reject' ? 0 : s === 'Warning' ? 1 : 2);
  return [...by.values()].sort((x, y) => rank(x.severity) - rank(y.severity) || y.items.length - x.items.length);
});

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

.draft__group summary {
  cursor: pointer;
}

.draft__findings {
  max-height: 20rem;
  overflow-y: auto;
  margin: tokens.$spacing-sm 0 0;
  font-size: tokens.$text-size-sm;
  color: tokens.$color-text-muted;
}

.draft__rejects {
  margin: 0;
  padding-left: tokens.$spacing-lg;
}
</style>
