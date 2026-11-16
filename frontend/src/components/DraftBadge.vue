<template>
  <!-- A draft, said in one word: the rejects it was stored despite open on hover, on a
       tap and on keyboard focus, one line per code. The full list stays on the upload
       result and the draft page. -->
  <span v-if="error" class="draft-badge__error">Draft status could not be loaded.</span>
  <template v-else-if="building?.draft">
    <button
      type="button"
      class="draft-badge"
      :aria-expanded="open"
      :aria-controls="panelId"
      @mouseenter="open = true"
      @mouseleave="open = false"
      @focus="open = true"
      @blur="open = false"
      @click="open = true"
      @keydown.esc="open = false"
    >
      Draft
    </button>
    <!-- ponytail: manual triggers, as a tap fires mouseenter before click: a toggle
         would close what the tap just opened. no-refocus: focus put back on the badge
         would open it again, and Tab could never leave. -->
    <q-menu v-model="open" no-parent-event no-focus no-refocus anchor="bottom left" self="top left">
      <div :id="panelId" class="draft-badge__panel" role="note">
        <p class="draft-badge__title">Stored despite these rejects</p>
        <ul class="draft-badge__list">
          <li v-for="r in building.reject_summary" :key="r.code">
            <strong>{{ r.code }}</strong>, {{ kg.format(r.count) }}×: {{ r.message }}
            <span class="draft-badge__todo">{{ r.what_to_do }}</span>
          </li>
        </ul>
        <p>Its figures stand; the home page does not count it.</p>
      </div>
    </q-menu>
  </template>
</template>

<script setup lang="ts">
import { ref, useId, watch } from 'vue';
import { fetchBuilding, type BuildingSummary } from '@/api/buildings';
import { kg } from '@/format';

const props = defineProps<{ buildingId: number }>();

const building = ref<BuildingSummary | null>(null);
const error = ref<string | null>(null);
const open = ref(false);
const panelId = useId();

watch(
  () => props.buildingId,
  async (id) => {
    building.value = null;
    error.value = null;
    open.value = false;
    try {
      const b = await fetchBuilding(id);
      if (id === props.buildingId) building.value = b; // a slower earlier reply is dropped
    } catch (e: unknown) {
      if (id === props.buildingId) error.value = e instanceof Error ? e.message : String(e);
    }
  },
  { immediate: true },
);
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.draft-badge {
  margin-left: tokens.$spacing-sm;
  padding: 0 tokens.$spacing-xs;
  border: tokens.$border-width solid tokens.$color-status-warning;
  border-radius: tokens.$radius-xs;
  background: tokens.$color-surface;
  color: tokens.$color-text;
  font: inherit;
  font-size: tokens.$text-size-sm;
  vertical-align: middle;
  cursor: help;
}

.draft-badge:focus-visible {
  outline: tokens.$border-width solid currentColor;
  outline-offset: 2px;
}

.draft-badge__error {
  margin-left: tokens.$spacing-sm;
  color: tokens.$color-text-muted;
  font-size: tokens.$text-size-sm;
}

.draft-badge__panel {
  max-width: min(26rem, calc(100vw - 2 * #{tokens.$spacing-lg}));
  padding: tokens.$spacing-md;
  font-size: tokens.$text-size-sm;
}

.draft-badge__panel p {
  margin: tokens.$spacing-xs 0 0;
}

.draft-badge__panel .draft-badge__title {
  margin: 0;
  font-weight: 600;
}

.draft-badge__todo {
  display: block;
  color: tokens.$color-text-muted;
}

.draft-badge__list {
  margin: tokens.$spacing-xs 0 0;
  padding-left: tokens.$spacing-lg;
}
</style>
