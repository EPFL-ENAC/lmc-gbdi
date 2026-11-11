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
          @update:model-value="(next: number) => router.push(buildingPath(next, next === other ? null : other))"
        />
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
            @update:model-value="(next: number | null) => router.push(buildingPath(id, next))"
          />
          <q-btn
            v-if="other !== null"
            flat
            no-caps
            label="Swap"
            @click="router.push(buildingPath(other, id))"
          />
        </div>
      </nav>
    </Teleport>
    <DraftPage v-if="draftOnly" :id="id" />
    <template v-else>
      <p v-if="current?.draft" class="building-draft" role="note">
        Draft, stored despite: {{ current.rejects.join('; ') }}. Its figures stand; the home page does not count it.
      </p>
      <router-view />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { code, fetchBuildings, noCarbon, type BuildingSummary } from '@/api/buildings';
import { buildingPath } from '@/buildingLayouts';
import DraftPage from '@/pages/DraftPage.vue';

const route = useRoute();
const router = useRouter();
const buildings = ref<BuildingSummary[]>([]);
const id = computed(() => Number(route.params.id));
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

.building-bar__compare {
  display: flex;
  align-items: center;
  gap: tokens.$spacing-sm;
  margin-left: auto;
}
</style>
