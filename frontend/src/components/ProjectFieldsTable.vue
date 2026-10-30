<template>
  <div class="fields">
    <q-btn unelevated no-caps class="btn-secondary fields__toggle" :label="`Columns: ${shown.length} of ${fields.length}`">
      <q-menu anchor="bottom left" self="top left">
        <div class="fields__menu">
          <details v-for="group in groups" :key="group.name" open class="fields__group">
            <summary class="fields__option">
              <input
                type="checkbox"
                :checked="group.shown === group.fields.length"
                :indeterminate.prop="group.shown > 0 && group.shown < group.fields.length"
                :aria-label="`${group.name}, ${group.shown} of ${group.fields.length} shown`"
                @change="toggle(group.fields, group.shown < group.fields.length)"
              />
              <span class="fields__grow">{{ group.name }}</span>
              <span class="fields__count">{{ group.shown }}/{{ group.fields.length }}</span>
            </summary>
            <label v-for="field in group.fields" :key="field.code" class="fields__option fields__option--field">
              <input
                type="checkbox"
                :checked="shown.includes(field.code)"
                :disabled="field.code === REQUIRED"
                @change="toggle([field], !shown.includes(field.code))"
              />
              {{ field.label }}
            </label>
          </details>
          <div class="fields__actions">
            <button type="button" class="btn-secondary" @click="shown = fields.map((f) => f.code)">
              Show all {{ fields.length }}
            </button>
            <button type="button" class="btn-secondary" @click="shown = [...DEFAULT_COLUMNS]">Reset</button>
          </div>
        </div>
      </q-menu>
    </q-btn>

    <q-table
      flat
      bordered
      hide-bottom
      :rows="[row]"
      :columns="columns"
      :visible-columns="shown"
      :row-key="REQUIRED"
      :pagination="{ rowsPerPage: 0 }"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import type { QTableColumn } from 'quasar';
import type { ProjectField } from '@/api/overview';

const props = defineProps<{ fields: ProjectField[] }>();

// The project ID always shows: it names the row, as in a table of many projects.
const REQUIRED = 'project_id';
const DEFAULT_COLUMNS = [
  REQUIRED,
  'project_name',
  'project_country',
  'building_use_type',
  'building_gross_floor_area',
  'lca_reference_study_period',
  'lca_cycle_system_boundary',
];
const shown = ref<string[]>([...DEFAULT_COLUMNS]);

const row = computed(() =>
  Object.fromEntries(props.fields.map((field) => [field.code, field.value ?? 'not declared'])),
);
const columns = computed<QTableColumn<Record<string, string>>[]>(() =>
  props.fields.map((field) => ({
    name: field.code,
    label: field.label,
    field: field.code,
    align: 'left',
    required: field.code === REQUIRED,
  })),
);
const groups = computed(() =>
  [...new Set(props.fields.map((field) => field.group))].map((name) => {
    const fields = props.fields.filter((field) => field.group === name);
    return { name, fields, shown: fields.filter((field) => shown.value.includes(field.code)).length };
  }),
);

function toggle(fields: ProjectField[], show: boolean) {
  const codes = fields.map((field) => field.code).filter((code) => code !== REQUIRED);
  shown.value = show
    ? [...new Set([...shown.value, ...codes])]
    : shown.value.filter((code) => !codes.includes(code));
}
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.fields {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: tokens.$spacing-md;
}

.fields > .q-table__container {
  align-self: stretch;
}

.fields__menu {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-md;
  min-width: 18rem;
  padding: tokens.$spacing-lg;
  font-size: tokens.$text-size-sm;
}

.fields__group summary {
  list-style: none;
  cursor: pointer;
}

.fields__group summary::-webkit-details-marker {
  display: none;
}

.fields__option {
  display: flex;
  align-items: center;
  gap: tokens.$spacing-sm;
  padding: tokens.$spacing-xs 0;
}

.fields__option--field {
  padding-left: tokens.$spacing-xl;
}

.fields__option input {
  accent-color: tokens.$color-primary;
}

.fields__grow {
  flex: 1;
  font-weight: tokens.$text-weight-medium;
}

.fields__count {
  color: tokens.$color-text-muted;
  font-variant-numeric: tabular-nums;
}

.fields__actions {
  display: flex;
  gap: tokens.$spacing-sm;
}

// Plain buttons in the menu take the kit's secondary button look at a smaller size.
.fields__actions .btn-secondary {
  padding: tokens.$spacing-xs tokens.$spacing-md;
  border: tokens.$border-width solid tokens.$color-border-control;
  border-radius: tokens.$radius-default;
  background: tokens.$color-surface-muted;
  font: inherit;
  cursor: pointer;
}
</style>
