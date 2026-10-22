import { defineRouter } from '#q-app';
import { createRouter, createWebHistory } from 'vue-router';

export default defineRouter(() =>
  createRouter({
    history: createWebHistory(import.meta.env.QUASAR_VUE_ROUTER_BASE),
    routes: [
      {
        path: '/',
        component: () => import('@/layouts/MainLayout.vue'),
        children: [{ path: '', component: () => import('@/pages/IndexPage.vue') }],
      },
    ],
  }),
);
