import { ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { code, fetchBuilding } from '@/api/buildings';
import { fetchOverview, type Overview } from '@/api/overview';

// The overview with the building's short name (its workbook's, "NL-23").
export type NamedOverview = Overview & { code: string };

// The overview of one building of the route, reloaded when its id changes: `id` by
// default (/buildings/:id), `other` for the second building of a comparison. Pages
// show `error` and the loading state themselves.
export function useOverview(param: 'id' | 'other' = 'id') {
  const route = useRoute();
  const overview = ref<NamedOverview | null>(null);
  const error = ref<string | null>(null);
  watch(
    () => route.params[param],
    async (id) => {
      overview.value = null;
      error.value = null;
      if (id === undefined) return;
      // Switching fast, a slower earlier reply must not overwrite the current one.
      const current = () => route.params[param] === id;
      try {
        const [o, summary] = await Promise.all([fetchOverview(Number(id)), fetchBuilding(Number(id))]);
        if (current()) overview.value = { ...o, code: code(summary) };
      } catch (e: unknown) {
        if (current()) error.value = e instanceof Error ? e.message : String(e);
      }
    },
    { immediate: true },
  );
  return { overview, error };
}

// Both buildings of /buildings/:id/…/compare/:other, loaded side by side.
export function useOverviewPair() {
  const a = useOverview('id');
  const b = useOverview('other');
  const error = ref<string | null>(null);
  watch([a.error, b.error], ([ea, eb]) => (error.value = ea ?? eb), { immediate: true });
  return { a: a.overview, b: b.overview, error };
}
