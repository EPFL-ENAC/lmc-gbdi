<template>
  <div class="fields">
    <q-btn unelevated no-caps class="btn-secondary fields__toggle" :label="`Fields: ${shown.length} of ${fields.length}`">
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
              <Term :name="field.label" :field="field.code" />
            </label>
          </details>
          <div class="fields__actions">
            <button type="button" class="btn-secondary" @click="shown = fields.map((f) => f.code)">
              Show all {{ fields.length }}
            </button>
            <button type="button" class="btn-secondary" @click="shown = [...DEFAULT_FIELDS]">Reset</button>
          </div>
        </div>
      </q-menu>
    </q-btn>

    <!-- Transposed (#96): one line per field, the groups side by side, so every field
         reads without scrolling sideways. Each field explains itself, and so do the
         OpenBDF values it holds. -->
    <div class="fields__groups">
      <table v-for="group in groups.filter((g) => g.shown > 0)" :key="group.name" class="fields__table">
        <caption>{{ group.name }}</caption>
        <tbody>
          <tr v-for="field in group.fields.filter((f) => shown.includes(f.code))" :key="field.code">
            <th scope="row"><Term :name="field.label" :field="field.code" /></th>
            <td :class="{ fields__missing: fieldText(field.value) === NOT_DECLARED }">
              <Term :name="fieldText(field.value)" />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import type { ProjectField } from '@/api/overview';
import Term from '@/components/atoms/Term.vue';
import { fieldText, NOT_DECLARED } from '@/format';

const props = defineProps<{ fields: ProjectField[] }>();

// The project ID always shows: it names the project.
const REQUIRED = 'project_id';
const DEFAULT_FIELDS = [
  REQUIRED,
  'project_name',
  'project_country',
  'project_city',
  'project_architect_engineer_name',
  'building_use_type',
  'building_residential_units',
  'building_construction_end_date',
  'building_gross_floor_area',
  'lca_reference_study_period',
  'lca_cycle_system_boundary',
];
const shown = ref<string[]>([...DEFAULT_FIELDS]);

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

.fields__groups {
  align-self: stretch;
  columns: 2 24rem;
  column-gap: tokens.$spacing-xl;
}

.fields__table {
  width: 100%;
  margin-bottom: tokens.$spacing-lg;
  border-collapse: collapse;
  break-inside: avoid;
  font-size: tokens.$text-size-sm;
}

.fields__table caption {
  padding-bottom: tokens.$spacing-xs;
  text-align: left;
  font-weight: tokens.$text-weight-medium;
}

.fields__table th,
.fields__table td {
  padding: tokens.$spacing-xs tokens.$spacing-sm;
  border-bottom: tokens.$border-width solid tokens.$color-border;
  text-align: left;
  vertical-align: top;
}

.fields__table th {
  width: 45%;
  font-weight: tokens.$text-weight-regular;
  color: tokens.$color-text-muted;
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

// A blank field is filled as an Info, the lowest severity: orange text would fail AA.
.fields__missing {
  background: tokens.$color-severity-info;
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
