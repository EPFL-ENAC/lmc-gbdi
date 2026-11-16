<template>
  <!-- The Overview's table of contents (globalbuildingdatainitiative/org#101): plain #hash
       links to the first panel of each group, in page order. A row of links on a wide
       screen, one "Sections" menu below 600 px. -->
  <nav class="sheet-toc" aria-label="Sections">
    <q-btn-dropdown v-if="$q.screen.lt.sm" no-caps outline dense color="dark" :label="`Sections: ${currentLabel}`">
      <q-list dense>
        <q-item
          v-for="stop in STOPS"
          :key="stop.id"
          v-close-popup
          tag="a"
          :href="`#${stop.id}`"
          :active="stop.id === current"
          active-class="sheet-toc__item--on"
          :aria-current="stop.id === current ? 'location' : undefined"
        >
          <q-item-section>{{ stop.label }}</q-item-section>
        </q-item>
      </q-list>
    </q-btn-dropdown>
    <div v-else class="sheet-toc__row">
      <a
        v-for="stop in STOPS"
        :key="stop.id"
        :href="`#${stop.id}`"
        class="sheet-toc__link"
        :class="{ 'sheet-toc__link--on': stop.id === current }"
        :aria-current="stop.id === current ? 'location' : undefined"
      >
        {{ stop.label }}
      </a>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

// One list feeds both forms. Each id sits on the first panel of its group in ProjectPage.
const STOPS = [
  { id: 'project-info', label: 'Project info' },
  { id: 'mass', label: 'Mass' },
  { id: 'emissions', label: 'Emissions' },
  { id: 'materials', label: 'Materials' },
  { id: 'data-quality', label: 'Data quality' },
] as const;

const current = ref<string>(STOPS[0].id);
const currentLabel = computed(() => STOPS.find((s) => s.id === current.value)?.label ?? STOPS[0].label);

let header: HTMLElement | null = null;
let resize: ResizeObserver | null = null;
let frame = 0;

// The current stop is the last one whose top reached the line under the header. It is read
// from the positions on each scroll: a #hash jump moves stops past that line without any
// of them crossing it, which an IntersectionObserver does not report.
function update() {
  frame = 0;
  // The stops land one spacing step under the header (scroll-margin-top); allow a few px more.
  const line = (header?.offsetHeight ?? 0) + 16;
  // At the end of the page the last stop is current, even when its sections are too
  // short to reach the line on a tall screen.
  if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 1) {
    current.value = STOPS[STOPS.length - 1].id;
    return;
  }
  current.value =
    [...STOPS].reverse().find((s) => (document.getElementById(s.id)?.getBoundingClientRect().top ?? Infinity) <= line)
      ?.id ?? STOPS[0].id;
}
const onScroll = () => {
  if (frame === 0) frame = requestAnimationFrame(update);
};

function measure() {
  // ProjectPage turns this into the stops' scroll-margin-top.
  document.documentElement.style.setProperty('--sheet-header-h', `${header?.offsetHeight ?? 0}px`);
  onScroll();
}

onMounted(() => {
  header = document.querySelector<HTMLElement>('.q-header');
  measure();
  window.addEventListener('scroll', onScroll, { passive: true });
  if (header) {
    resize = new ResizeObserver(measure);
    resize.observe(header);
  }
});

onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll);
  cancelAnimationFrame(frame);
  resize?.disconnect();
  document.documentElement.style.removeProperty('--sheet-header-h');
});
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

// One line; at 360 px it scrolls inside itself, never the page.
.sheet-toc__row {
  display: flex;
  gap: tokens.$spacing-xs;
  overflow-x: auto;
  scrollbar-width: none;
}

.sheet-toc__link {
  padding: tokens.$spacing-xs tokens.$spacing-sm;
  border-radius: tokens.$radius-panel;
  color: tokens.$color-text-muted;
  text-decoration: none;
  white-space: nowrap;
}

.sheet-toc__link:hover,
.sheet-toc__link:focus-visible {
  color: tokens.$color-text;
}

.sheet-toc__link--on,
.sheet-toc__item--on {
  background: tokens.$color-surface-highlight;
  color: tokens.$color-text;
  font-weight: 600;
}
</style>
