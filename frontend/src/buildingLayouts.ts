// The design demo's seven layouts of one building. Overview and Spread are the two
// the team is choosing between; `demo` is each one's old /demo/project* address.
export const LAYOUTS = [
  { label: 'Overview', value: '', demo: 'demo/project', page: () => import('@/pages/ProjectPage.vue') },
  { label: 'Spread', value: '/spread', demo: 'demo/project_1', page: () => import('@/pages/ProjectSpreadPage.vue') },
  { label: 'Section', value: '/section', demo: 'demo/project_2', page: () => import('@/pages/ProjectSectionPage.vue') },
  { label: 'Sheet', value: '/sheet', demo: 'demo/project_3', page: () => import('@/pages/ProjectSheetPage.vue') },
  { label: 'Benchmark', value: '/benchmark', demo: 'demo/project_4', page: () => import('@/pages/ProjectBenchmarkPage.vue') },
  { label: 'Time', value: '/time', demo: 'demo/project_5', page: () => import('@/pages/ProjectTimePage.vue') },
  { label: 'Passport', value: '/passport', demo: 'demo/project_6', page: () => import('@/pages/ProjectPassportPage.vue') },
];
