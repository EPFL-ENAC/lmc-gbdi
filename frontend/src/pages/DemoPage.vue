<template>
  <q-page class="page-grid">
    <!-- One statement, two tones: the second half fades to Grey Text (p.35) -->
    <section>
      <h1>Open Data<br /><span class="text-display-lead">Better Buildings</span></h1>
      <p class="text-lead">
        Design resilient buildings with better climate performance. Manage your portfolio's footprint.
        Develop effective climate policy. Use our data and tools to assess and reduce resource use and
        embodied carbon emissions.
      </p>
      <div class="demo-actions">
        <q-btn unelevated no-caps color="primary" label="Explore the data" to="/demo/project" />
        <q-btn unelevated no-caps class="btn-secondary" label="Download the methodology" />
      </div>
    </section>

    <!-- The one set of hero cards on the page; every number carries its source -->
    <section class="grid-3-col" aria-label="Key figures">
      <div v-for="hero in heroes" :key="hero.number" class="gbdi-hero-card" :class="`gbdi-hero-card--${hero.tone}`">
        <p class="gbdi-hero-card__number">{{ hero.number }}</p>
        <p class="gbdi-hero-card__text">{{ hero.text }}<sup>1</sup></p>
      </div>
    </section>

    <section class="grid-3-col">
      <article class="gbdi-card">
        <svg class="gbdi-card__illustration gbdi-illustration" viewBox="0 0 120 120" width="120" height="120" aria-hidden="true">
          <circle cx="60" cy="60" r="48" />
          <ellipse cx="60" cy="60" rx="32" ry="48" />
          <ellipse cx="60" cy="60" rx="14" ry="48" />
          <path d="M60 12v96" />
          <circle class="accent" cx="38" cy="36" r="4" />
          <circle class="accent" cx="74" cy="52" r="4" />
          <circle class="accent" cx="50" cy="78" r="4" />
          <circle class="accent" cx="88" cy="72" r="4" />
        </svg>
        <h2 class="gbdi-card__title">Better data</h2>
        <p class="gbdi-card__body">
          Open, comparable building and whole-life carbon data, collected with one global methodology.
        </p>
      </article>
      <article class="gbdi-card">
        <svg class="gbdi-card__illustration gbdi-illustration" viewBox="0 0 120 120" width="120" height="120" aria-hidden="true">
          <path d="M14 58l52-28 40 22-52 28z" />
          <path d="M14 58v24l40 22V80" />
          <path d="M54 104l52-28V52" />
          <path class="accent" d="M40 54l10-5 8 4-10 5z" />
          <path class="accent" d="M60 49l10-5 8 4-10 5z" />
        </svg>
        <h2 class="gbdi-card__title">Better materials</h2>
        <p class="gbdi-card__body">
          Material hotspots that show where a low-carbon alternative changes the result most.
        </p>
      </article>
      <article class="gbdi-card">
        <svg class="gbdi-card__illustration gbdi-illustration" viewBox="0 0 120 120" width="120" height="120" aria-hidden="true">
          <path class="accent" d="M34 30l26-14 26 14-26 14z" />
          <path d="M34 30v58l26 14V44" />
          <path d="M60 102l26-14V30" />
          <path d="M64 52l18-10M64 64l18-10M64 76l18-10M64 88l18-10" />
        </svg>
        <h2 class="gbdi-card__title">Better design</h2>
        <p class="gbdi-card__body">
          Benchmarks that let a design team compare an option against real buildings, early enough to
          matter.
        </p>
      </article>
    </section>

    <footer class="u-text-muted">
      <ol>
        <li>Figures as printed in the GBDI Brand Guidelines v01 (2024); cite the underlying studies in production.</li>
      </ol>
    </footer>
  </q-page>
</template>

<script setup lang="ts">
const heroes = [
  { tone: 'green', number: '42%', text: 'of global carbon emissions can be reduced by building better.' },
  { tone: 'blue', number: '50–90%', text: "of a new building's whole-life carbon is embodied carbon." },
  { tone: 'purple', number: '50–70%', text: 'less embodied carbon from materials is possible today.' },
];
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.demo-actions {
  display: flex;
  flex-wrap: wrap;
  gap: tokens.$spacing-sm;
}
</style>
