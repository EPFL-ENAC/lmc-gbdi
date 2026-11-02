<template>
  <!-- A headline figure on a pastel fill (brand guidelines p.17, p.25): the number, then
       one short line that opens with its unit. One set per page. A `to` makes the whole
       figure a link. -->
  <component :is="to ? RouterLink : 'div'" :to="to" class="big-number" :class="[`big-number--${tone}`, { 'big-number--link': to }]">
    <p v-if="label" class="big-number__label">{{ label }}</p>
    <p class="big-number__value">{{ value }}</p>
    <p class="big-number__text"><slot /></p>
  </component>
</template>

<script setup lang="ts">
import { RouterLink } from 'vue-router';

defineProps<{
  value: string;
  tone: 'green' | 'blue' | 'purple' | 'orange';
  label?: string; // whose figure, when a page sets two side by side
  to?: string;
}>();
</script>

<style scoped lang="scss">
@use 'sass:map';
@use '@/css/02-tokens' as tokens;

.big-number {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-sm;
  padding: tokens.$big-number-padding;
  border-radius: tokens.$big-number-radius;
}

.big-number p {
  margin: 0;
}

.big-number__label {
  font-weight: tokens.$text-weight-bold;
}

.big-number__value {
  font-family: tokens.$big-number-value-font-family;
  font-size: tokens.$big-number-value-font-size;
  line-height: tokens.$big-number-value-line-height;
  letter-spacing: tokens.$text-letter-spacing-display;
}

.big-number__text {
  font-size: tokens.$big-number-text-font-size;
  line-height: tokens.$big-number-text-line-height;
}

@each $tone, $t in tokens.$big-number-tones {
  .big-number--#{$tone} {
    background-color: map.get($t, bg);

    .big-number__value {
      color: map.get($t, number);
    }

    .big-number__text {
      color: map.get($t, text);
    }
  }
}

.big-number--link {
  text-decoration: none;
}

.big-number--link:hover,
.big-number--link:focus-visible {
  outline: tokens.$border-width solid currentColor;
}
</style>
