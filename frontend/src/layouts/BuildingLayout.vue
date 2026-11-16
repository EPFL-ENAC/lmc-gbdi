<template>
  <!-- One stored building: which one, and which other building, if any, sits beside it.
       The bar goes into the fixed header, so it stays in view while the page scrolls (#93). -->
  <div>
    <Teleport defer to="#building-bar">
      <nav class="building-bar" aria-label="Building">
        <router-link class="link" to="/buildings">All buildings</router-link>
        <q-select
          :model-value="id"
          :options="options"
          option-label="label"
          option-value="id"
          emit-value
          map-options
          dense
          outlined
          options-dense
          label="Building"
          class="building-bar__pick"
          @update:model-value="(next: number) => router.push({ path: buildingPath(next, next === other ? null : other), query: route.query })"
        />
        <!-- Below 600 px the display controls fold behind one button, so the bar keeps two
             lines; the page puts its current basis in the button's label. -->
        <q-btn
          v-if="$q.screen.lt.sm && !draftOnly"
          outline
          dense
          no-caps
          color="dark"
          class="building-bar__display"
          :aria-expanded="open"
          aria-controls="building-bar-more"
          @click="open = !open"
        >
          Display<span id="display-summary" />
        </q-btn>
        <div v-show="!$q.screen.lt.sm || (open && !draftOnly)" id="building-bar-more" class="building-bar__more">
          <!-- The page's own controls, such as the Overview's basis, teleport here. -->
          <div id="basis-control" class="building-bar__page" />
          <div v-if="!draftOnly" class="building-bar__compare">
            <q-select
              :model-value="other"
              :options="comparable.filter((o) => o.id !== id)"
              option-label="label"
              option-value="id"
              emit-value
              map-options
              dense
              outlined
              options-dense
              clearable
              label="Compare with"
              class="building-bar__pick"
              @update:model-value="(next: number | null) => router.push({ path: buildingPath(id, next), query: route.query })"
            />
            <q-btn
              v-if="other !== null"
              flat
              no-caps
              label="Swap"
              @click="router.push({ path: buildingPath(other, id), query: route.query })"
            />
          </div>
        </div>
        <!-- The page's table of contents, the bar's second line (org#101). -->
        <div id="sheet-toc" class="building-bar__toc" />
      </nav>
    </Teleport>
    <DraftPage v-if="draftOnly" :id="id" />
    <!-- Not before the list settles: until then a carbon-blocked draft looks like any
         building, and the Overview would ask for figures it cannot have (409). -->
    <template v-else-if="settled">
      <p v-if="current?.draft" class="building-draft" role="note">
        Draft, stored despite: {{ current.rejects.join('; ') }}. Its figures stand; the home page does not count it.
      </p>
      <router-view />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { code, fetchBuildings, noCarbon, type BuildingSummary } from '@/api/buildings';
import { buildingPath } from '@/buildingLayouts';
import DraftPage from '@/pages/DraftPage.vue';

const route = useRoute();
const router = useRouter();
const buildings = ref<BuildingSummary[]>([]);
const settled = ref(false);
const open = ref(false); // the folded display controls, below 600 px
const id = computed(() => Number(route.params.id));
// Another building starts with the controls folded.
watch(id, () => (open.value = false));
const other = computed(() => (route.params.other === undefined ? null : Number(route.params.other)));
const options = computed(() =>
  buildings.value.map((b) => ({ id: b.id, label: `${code(b)}, ${b.project_name ?? 'unnamed'}` })),
);
const comparable = computed(() => options.value.filter((o) => !buildings.value.some((b) => b.id === o.id && noCarbon(b))));
// A draft whose rejects block carbon has no overview to read: it shows its draft page.
const current = computed(() => buildings.value.find((b) => b.id === id.value));
const draftOnly = computed(() => current.value !== undefined && noCarbon(current.value));

onMounted(async () => {
  // The bar works without the list: only the two building menus need it.
  buildings.value = await fetchBuildings().catch(() => []);
  settled.value = true;
});
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.building-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: tokens.$spacing-md;
  padding: tokens.$spacing-sm tokens.$spacing-lg;
  border-top: tokens.$border-width solid tokens.$color-border;
  background: tokens.$color-surface;
}

.building-draft {
  margin: 0;
  padding: tokens.$spacing-sm tokens.$spacing-lg;
  background: tokens.$color-surface-highlight;
  font-size: tokens.$text-size-sm;
}

.building-bar__pick {
  width: 14rem;
}

.building-bar__page {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: tokens.$spacing-md;
  min-width: 0;
}

.building-bar__toc {
  flex-basis: 100%;
  min-width: 0;
}

.building-bar__toc:empty {
  display: none;
}

.building-bar__compare {
  display: flex;
  align-items: center;
  gap: tokens.$spacing-sm;
  margin-left: auto;
}

// Wide: a wrapper the flex row does not see, so the bar lays out as before.
.building-bar__more {
  display: contents;
}

// Below 600 px: the link and the building on line 1, Display and Sections on line 2,
// and the opened display controls under both.
@media (max-width: 599.98px) {
  .building-bar {
    gap: tokens.$spacing-sm;
    padding: tokens.$spacing-sm tokens.$spacing-md;
  }

  // A basis wide enough that Display and Sections wrap to line 2.
  // The building takes the rest of line 1 at every width below 600 px, so Display and
  // Sections always start line 2.
  .building-bar > .building-bar__pick {
    flex-basis: calc(100% - 8rem);
  }

  .building-bar__pick {
    flex: 1 1 12rem;
    width: auto;
    min-width: 0;
  }

  .building-bar__toc {
    flex: 1 1 0;
  }

  .building-bar__more {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: tokens.$spacing-sm;
    flex-basis: 100%;
    min-width: 0;
    order: 1;
  }

  .building-bar__compare {
    margin-left: 0;
    width: 100%;
  }
}
</style>
