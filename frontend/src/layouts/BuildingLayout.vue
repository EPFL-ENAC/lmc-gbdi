<template>
  <!-- One stored building: which one, how to read it (the design demo's layouts), and
       a way to set it beside another. -->
  <div>
    <nav class="building-bar" aria-label="Building">
      <router-link class="link" to="/buildings">All buildings</router-link>
      <p class="building-bar__code">{{ current ? code(current) : '' }}</p>
      <q-btn-toggle
        :model-value="layout"
        :options="LAYOUTS.map(({ label, value }) => ({ label, value }))"
        no-caps
        unelevated
        toggle-color="primary"
        color="white"
        text-color="dark"
        class="building-bar__layouts"
        @update:model-value="(value: string) => router.push(`/buildings/${id}${value}`)"
      />
      <q-select
        :model-value="null"
        :options="others"
        option-label="label"
        option-value="id"
        emit-value
        map-options
        dense
        outlined
        label="Compare with"
        class="building-bar__compare"
        @update:model-value="(other: number) => router.push({ path: '/buildings/compare', query: { a: id, b: other } })"
      />
    </nav>
    <router-view />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { code, fetchBuildings, type BuildingSummary } from '@/api/buildings';
import { LAYOUTS } from '@/buildingLayouts';

const route = useRoute();
const router = useRouter();
const buildings = ref<BuildingSummary[]>([]);
const id = computed(() => Number(route.params.id));
const layout = computed(() => LAYOUTS.find((l) => l.value && route.path.endsWith(l.value))?.value ?? '');
const current = computed(() => buildings.value.find((b) => b.id === id.value));
const others = computed(() =>
  buildings.value
    .filter((b) => b.id !== id.value)
    .map((b) => ({ id: b.id, label: `${code(b)}, ${b.project_name ?? 'unnamed'}` })),
);

onMounted(async () => {
  // The bar works without the list: only the compare menu and the code need it.
  buildings.value = await fetchBuildings().catch(() => []);
});
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.building-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: tokens.$spacing-lg;
  padding: tokens.$spacing-sm tokens.$spacing-page;
  border-bottom: tokens.$border-width solid tokens.$color-border;
  background: tokens.$color-surface;
}

.building-bar__code {
  margin: 0;
  font-weight: tokens.$text-weight-bold;
}

.building-bar__layouts {
  border: tokens.$border-width solid tokens.$color-border;
}

.building-bar__compare {
  min-width: 18rem;
  margin-left: auto;
}
</style>
