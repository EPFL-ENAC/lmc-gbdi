<template>
  <!-- Every top 10 opens onto the rest of the list, the same way on every layout. -->
  <button v-if="count > 0" type="button" class="show-more" :aria-expanded="open" @click="open = !open">
    {{ open ? 'Show the top 10 only' : `Show the ${count} remaining ${noun}` }}
  </button>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ count: number; noun?: string }>(), { noun: 'materials' });
const open = defineModel<boolean>({ default: false });
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.show-more {
  align-self: flex-start;
  padding: 0;
  border: 0;
  background: none;
  font: inherit;
  font-size: tokens.$text-size-sm;
  color: tokens.$color-text-link;
  text-decoration: underline;
  text-underline-offset: 0.125rem;
  cursor: pointer;
}
</style>
