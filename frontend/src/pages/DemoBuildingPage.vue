<template>
  <!-- The design demo's layouts were drawn on the AT workbook; they now show AT-09, the
       same project, as stored. This page only finds it and goes there. -->
  <q-page class="page-grid">
    <p v-if="error" class="gbdi-card" role="alert">The buildings could not be loaded. {{ error }}</p>
    <p v-else-if="missing" class="gbdi-card">
      The demo shows {{ DEMO_FILE }}, which is not loaded yet.
      <router-link class="link" to="/buildings">Add it from the building list</router-link>.
    </p>
    <p v-else class="u-text-muted">Opening the demo building…</p>
  </q-page>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { fetchBuildings } from '@/api/buildings';

const DEMO_FILE = 'AT-09.xlsx';

const props = defineProps<{ layout: string }>();
const router = useRouter();
const error = ref<string | null>(null);
const missing = ref(false);

onMounted(async () => {
  try {
    const demo = (await fetchBuildings()).find((b) => b.file_name === DEMO_FILE);
    if (demo) await router.replace(`/buildings/${demo.id}${props.layout}`);
    else missing.value = true;
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e);
  }
});
</script>
