<template>
  <!-- org#115: the publication a project comes from, so its users can cite it. Opens like
       the Draft badge: hover, tap and keyboard focus. One root, so a parent's @click.stop
       keeps a tap in a list row from opening the row. -->
  <span v-if="reference || doi" class="reference-badge">
    <button
      type="button"
      class="reference-badge__button"
      :aria-expanded="open"
      :aria-controls="panelId"
      @mouseenter="show"
      @mouseleave="closeSoon"
      @focus="show"
      @blur="closeSoon"
      @click="show"
      @keydown.esc="open = false"
    >
      Reference
    </button>
    <!-- ponytail: same manual triggers as DraftBadge.vue, for the same reasons. Unlike
         it, the pointer may move into the panel to select and copy the citation. -->
    <q-menu v-model="open" no-parent-event no-focus no-refocus anchor="bottom left" self="top left">
      <div :id="panelId" class="reference-badge__panel"
        role="note"
        @mouseenter="overPanel = true"
        @mouseleave="
          overPanel = false;
          closeSoon();
        "
      >
        <p class="reference-badge__title">Source publication</p>
        <p v-if="reference">{{ reference }}</p>
        <p v-if="doi">
          DOI:
          <a v-if="doiHref" :href="doiHref" target="_blank" rel="noopener noreferrer">{{ doi }}</a>
          <template v-else>{{ doi }}</template>
        </p>
      </div>
    </q-menu>
  </span>
</template>

<script setup lang="ts">
import { computed, ref, useId } from 'vue';

const props = defineProps<{ reference: string | null; doi: string | null }>();

const open = ref(false);
const panelId = useId();
const overPanel = ref(false);

// A short delay lets the pointer cross from the button to the panel; a press in the
// panel blurs the button, so blur closes only when the pointer is not over the panel.
let timer: ReturnType<typeof setTimeout> | undefined;
function show() {
  clearTimeout(timer);
  open.value = true;
}
function closeSoon() {
  clearTimeout(timer);
  timer = setTimeout(() => {
    if (!overPanel.value) open.value = false;
  }, 150);
}

// Only an http(s) link or a bare DOI (10.…) becomes a link: no other scheme reaches an href.
const doiHref = computed(() => {
  const d = props.doi?.trim();
  if (!d) return null;
  if (/^https?:\/\//i.test(d)) return d;
  if (d.startsWith('10.')) return `https://doi.org/${d}`;
  return null;
});
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.reference-badge__button {
  margin-left: tokens.$spacing-sm;
  padding: 0 tokens.$spacing-xs;
  border: tokens.$border-width solid tokens.$color-border-control;
  border-radius: tokens.$radius-xs;
  background: tokens.$color-surface;
  color: tokens.$color-text;
  font: inherit;
  font-size: tokens.$text-size-sm;
  vertical-align: middle;
  cursor: help;
}

.reference-badge__button:focus-visible {
  outline: tokens.$border-width solid currentColor;
  outline-offset: 2px;
}

.reference-badge__panel {
  max-width: min(26rem, calc(100vw - 2 * #{tokens.$spacing-lg}));
  padding: tokens.$spacing-md;
  font-size: tokens.$text-size-sm;
  overflow-wrap: anywhere;
  user-select: text;
}

.reference-badge__panel p {
  margin: tokens.$spacing-xs 0 0;
}

.reference-badge__panel .reference-badge__title {
  margin: 0;
  font-weight: 600;
}
</style>
