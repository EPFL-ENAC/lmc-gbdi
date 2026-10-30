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
          { path: 'buildings', component: () => import('@/pages/BuildingsPage.vue') },
          { path: 'buildings/compare', component: () => import('@/pages/ComparePage.vue') },
          // A stored building in the two layouts the team is choosing between.
          {
            path: 'buildings/:id(\\d+)',
            component: () => import('@/layouts/BuildingLayout.vue'),
            children: [
              { path: '', component: () => import('@/pages/ProjectPage.vue') },
              { path: 'spread', component: () => import('@/pages/ProjectSpreadPage.vue') },
            ],
          },
          { path: 'demo', component: () => import('@/pages/DemoPage.vue') },
          { path: 'demo/project', component: () => import('@/pages/ProjectPage.vue') },
          // Three alternative layouts of the same overview, to compare.
          { path: 'demo/project_1', component: () => import('@/pages/ProjectSpreadPage.vue') },
          { path: 'demo/project_2', component: () => import('@/pages/ProjectSectionPage.vue') },
          { path: 'demo/project_3', component: () => import('@/pages/ProjectSheetPage.vue') },
          // Three more, each after a practice of the building LCA field.
          { path: 'demo/project_4', component: () => import('@/pages/ProjectBenchmarkPage.vue') },
          { path: 'demo/project_5', component: () => import('@/pages/ProjectTimePage.vue') },
          { path: 'demo/project_6', component: () => import('@/pages/ProjectPassportPage.vue') },
        ],
      },
    ],
  }),
);
