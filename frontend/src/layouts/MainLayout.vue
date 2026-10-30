<template>
  <q-layout view="hHh lpR fFf">
    <q-header class="bg-white text-dark" bordered>
      <q-toolbar>
        <q-toolbar-title>
          <router-link to="/buildings">
            <img src="/logo.png" alt="Global Building Data Initiative" width="145" height="32" />
          </router-link>
        </q-toolbar-title>
        <nav class="main-nav" aria-label="Main">
          <router-link class="main-nav__link" to="/buildings">Buildings</router-link>
          <router-link class="main-nav__link" to="/buildings/compare">Compare</router-link>
          <router-link class="main-nav__link" to="/">Design demo</router-link>
        </nav>
      </q-toolbar>
    </q-header>
    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.main-nav {
  display: flex;
  gap: tokens.$spacing-lg;
}

.main-nav__link {
  color: tokens.$color-text;
  text-decoration: none;
}

.main-nav__link.router-link-exact-active {
  color: tokens.$color-primary-strong;
  font-weight: tokens.$text-weight-bold;
}

.main-nav__link:hover,
.main-nav__link:focus-visible {
  text-decoration: underline;
}
</style>
