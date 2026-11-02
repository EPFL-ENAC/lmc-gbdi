import { ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { fetchOverview, type Overview } from '@/api/overview';

// The overview of one building of the route, reloaded when its id changes: `id` by
// default (/buildings/:id), `other` for the second building of a comparison. Pages
// show `error` and the loading state themselves.
export function useOverview(param: 'id' | 'other' = 'id') {
  const route = useRoute();
  const overview = ref<Overview | null>(null);
  const error = ref<string | null>(null);
  watch(
    () => route.params[param],
    async (id) => {
      overview.value = null;
      error.value = null;
      if (id === undefined) return;
      try {
        overview.value = await fetchOverview(Number(id));
      } catch (e: unknown) {
        error.value = e instanceof Error ? e.message : String(e);
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
