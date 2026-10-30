<template>
  <q-page padding>
    <h1>GBDI</h1>
    <article class="gbdi-card">
      <h3 class="gbdi-card__title">API</h3>
      <p class="gbdi-card__body">
        <q-badge :color="status === 'ok' ? 'positive' : 'negative'" :label="status" />
      </p>
    </article>
    <ul>
      <li><router-link class="link" to="/buildings">Buildings, from the database</router-link></li>
      <li><router-link class="link" to="/demo">Design demo</router-link></li>
      <li><router-link class="link" to="/demo/project">Project overview</router-link></li>
      <li><router-link class="link" to="/demo/project_1">Layout 1, spread</router-link></li>
      <li><router-link class="link" to="/demo/project_2">Layout 2, section</router-link></li>
      <li><router-link class="link" to="/demo/project_3">Layout 3, sheet</router-link></li>
      <li><router-link class="link" to="/demo/project_4">Layout 4, benchmark</router-link></li>
      <li><router-link class="link" to="/demo/project_5">Layout 5, time</router-link></li>
      <li><router-link class="link" to="/demo/project_6">Layout 6, passport</router-link></li>
    </ul>
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
