import { defineRouter } from '#q-app';
import { createRouter, createWebHistory } from 'vue-router';

export default defineRouter(() =>
  createRouter({
    history: createWebHistory(import.meta.env.QUASAR_VUE_ROUTER_BASE),
    routes: [
      {
        path: '/',
        component: () => import('@/layouts/MainLayout.vue'),
        children: [
          { path: '', component: () => import('@/pages/DemoPage.vue') },
          { path: 'demo', redirect: '/' },
          { path: 'buildings', component: () => import('@/pages/BuildingsPage.vue') },
          { path: 'buildings/compare', component: () => import('@/pages/ComparePage.vue') },
          // A stored building, alone or beside another.
          {
            path: 'buildings/:id(\\d+)',
            component: () => import('@/layouts/BuildingLayout.vue'),
            children: [
              { path: '', component: () => import('@/pages/ProjectPage.vue') },
              { path: 'compare/:other(\\d+)', component: () => import('@/pages/ComparePage.vue') },
            ],
          },
          // The design demo's tabs became the one view (globalbuildingdatainitiative/org#97);
          // their old addresses still open it.
          {
            path: 'buildings/:id(\\d+)/:tab(spread|section|sheet|time|passport)/:rest(compare/\\d+)?',
            redirect: (to) => `/buildings/${String(to.params.id)}${to.params.rest ? `/${String(to.params.rest)}` : ''}`,
          },
          // The demo's old /demo/project* addresses, on its building (AT-09) from the database.
          { path: 'demo/project:variant(_\\d)?', component: () => import('@/pages/DemoBuildingPage.vue') },
        ],
      },
    ],
  }),
);
