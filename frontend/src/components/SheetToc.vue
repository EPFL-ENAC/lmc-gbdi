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
let measure = () => {};
let resize: ResizeObserver | null = null;
let observer: IntersectionObserver | null = null;
const above = new Set<string>();

// The stops whose top passed the line under the header; the last of them is current.
function watchStops(headerHeight: number) {
  observer?.disconnect();
  above.clear();
  observer = new IntersectionObserver(
    (entries) => {
      for (const e of entries) {
        const passed = e.boundingClientRect.top < headerHeight + 1;
        if (passed) above.add(e.target.id);
        else above.delete(e.target.id);
      }
      current.value = [...STOPS].reverse().find((s) => above.has(s.id))?.id ?? STOPS[0].id;
    },
    // A band one pixel high just under the header: a stop crosses it on the way up or down.
    { rootMargin: `-${headerHeight}px 0px -${Math.max(window.innerHeight - headerHeight - 1, 0)}px 0px` },
  );
  for (const s of STOPS) {
    const el = document.getElementById(s.id);
    if (el) observer.observe(el);
  }
}

onMounted(() => {
  header = document.querySelector<HTMLElement>('.q-header');
  measure = () => {
    const h = header?.offsetHeight ?? 0;
    // ProjectPage turns this into the stops' scroll-margin-top.
    document.documentElement.style.setProperty('--sheet-header-h', `${h}px`);
    watchStops(h);
  };
  measure();
  // The band depends on the window height too (a phone's address bar).
  window.addEventListener('resize', measure);
  if (header) {
    resize = new ResizeObserver(measure);
    resize.observe(header);
  }
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', measure);
  resize?.disconnect();
  observer?.disconnect();
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
