// The design demo's seven layouts of one building, each with its own way of setting a
// second building beside it (`compare`). Overview and Spread are the two the team is
// choosing between; `demo` is each one's old /demo/project* address.
export const LAYOUTS = [
  {
    label: 'Overview',
    value: '',
    demo: 'demo/project',
    page: () => import('@/pages/ProjectPage.vue'),
    compare: () => import('@/pages/ComparePage.vue'),
  },
  {
    label: 'Spread',
    value: '/spread',
    demo: 'demo/project_1',
    page: () => import('@/pages/ProjectSpreadPage.vue'),
    compare: () => import('@/pages/ProjectSpreadComparePage.vue'),
  },
  {
    label: 'Section',
    value: '/section',
    demo: 'demo/project_2',
    page: () => import('@/pages/ProjectSectionPage.vue'),
    compare: () => import('@/pages/ProjectSectionComparePage.vue'),
  },
  {
    label: 'Sheet',
    value: '/sheet',
    demo: 'demo/project_3',
    page: () => import('@/pages/ProjectSheetPage.vue'),
    compare: () => import('@/pages/ProjectSheetComparePage.vue'),
  },
  {
    label: 'Benchmark',
    value: '/benchmark',
    demo: 'demo/project_4',
    page: () => import('@/pages/ProjectBenchmarkPage.vue'),
    compare: () => import('@/pages/ProjectBenchmarkComparePage.vue'),
  },
  {
    label: 'Time',
    value: '/time',
    demo: 'demo/project_5',
    page: () => import('@/pages/ProjectTimePage.vue'),
    compare: () => import('@/pages/ProjectTimeComparePage.vue'),
  },
  {
    label: 'Passport',
    value: '/passport',
    demo: 'demo/project_6',
    page: () => import('@/pages/ProjectPassportPage.vue'),
    compare: () => import('@/pages/ProjectPassportComparePage.vue'),
  },
];

// /buildings/8/spread, and /buildings/8/spread/compare/9 when a second building is set beside it.
export const buildingPath = (id: number, layout: string, other: number | null = null) =>
  `/buildings/${id}${layout}${other === null ? '' : `/compare/${other}`}`;
