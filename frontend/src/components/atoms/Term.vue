<template>
  <!-- A name the reader may not know, explained on hover or focus from lmc-openbdf's
       own model. A name the glossary does not explain stays plain text. -->
  <span v-if="meaning" class="term" tabindex="0">{{ name }}<q-tooltip max-width="22rem">{{ meaning }}</q-tooltip></span>
  <template v-else>{{ name }}</template>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { termKey, useGlossary } from '@/composables/useGlossary';

const props = defineProps<{
  name: string;
  field?: string; // a project field code: its description, whatever the label says
}>();

const glossary = useGlossary();
const meaning = computed(() =>
  props.field ? glossary.value.fields[props.field] : glossary.value.terms[termKey(props.name)],
);
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.term {
  text-decoration: underline dotted;
  text-underline-offset: 0.2em;
  cursor: help;
}

.term:focus-visible {
  outline: tokens.$border-width solid currentColor;
}
</style>
