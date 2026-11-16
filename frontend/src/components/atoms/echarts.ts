import { defineAsyncComponent, h } from 'vue';

// ECharts loads with a chart only, in its own chunk. Each chart passes the module that
// registers its own series type (echart-line.ts, …), so the wrapper carries none.
export const asyncEChart = (series: () => Promise<unknown>) =>
  defineAsyncComponent({
    loader: () => Promise.all([import('./EChart.vue'), series()]).then(([wrapper]) => wrapper),
    errorComponent: () => h('p', { class: 'u-text-muted' }, 'The chart failed to load.'),
  });

// ECharts parses and blends colours, so a var(--…) goes in as its value, read on `el`.
export const cssColor = (value: string, el: Element = document.documentElement) =>
  value.startsWith('var(') ? getComputedStyle(el).getPropertyValue(value.slice(4, -1)).trim() : value;
