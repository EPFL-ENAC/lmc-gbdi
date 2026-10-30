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
          { path: '', component: () => import('@/pages/IndexPage.vue') },
          { path: 'demo', component: () => import('@/pages/DemoPage.vue') },
          { path: 'demo/project', component: () => import('@/pages/ProjectPage.vue') },
          // Three alternative layouts of the same overview, to compare.
          { path: 'demo/project_1', component: () => import('@/pages/ProjectSpreadPage.vue') },
          { path: 'demo/project_2', component: () => import('@/pages/ProjectSectionPage.vue') },
          { path: 'demo/project_3', component: () => import('@/pages/ProjectSheetPage.vue') },
        ],
      },
    ],
  }),
);
