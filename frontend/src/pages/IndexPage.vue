<template>
  <q-page padding>
    <h1>GBDI</h1>
    <article class="gbdi-card">
      <h3 class="gbdi-card__title">API</h3>
      <p class="gbdi-card__body">
        <q-badge :color="status === 'ok' ? 'positive' : 'negative'" :label="status" />
      </p>
    </article>
  </q-page>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';

// /api/ready runs SELECT 1, so "ok" means frontend -> backend -> postgres works.
const status = ref('checking');

onMounted(async () => {
  const response = await fetch('/api/ready');
  status.value = response.ok ? 'ok' : `error ${response.status}`;
});
</script>
