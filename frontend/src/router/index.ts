import { defineRouter } from '#q-app';
import { createRouter, createWebHistory } from 'vue-router';
import { LAYOUTS } from '@/buildingLayouts';

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
          // A stored building in each layout of the design demo, alone or beside another.
          {
            path: 'buildings/:id(\\d+)',
            component: () => import('@/layouts/BuildingLayout.vue'),
            children: LAYOUTS.flatMap((l) => [
              { path: l.value.slice(1), component: l.page, meta: { layout: l.value } },
              {
                path: `${l.value.slice(1)}${l.value ? '/' : ''}compare/:other(\\d+)`,
                component: l.compare,
                meta: { layout: l.value },
              },
            ]),
          },
          // The demo's layouts, on its building (AT-09) from the database.
          ...LAYOUTS.map((l) => ({
            path: l.demo,
            component: () => import('@/pages/DemoBuildingPage.vue'),
            props: { layout: l.value },
          })),
        ],
      },
    ],
  }),
);
