import { ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { fetchOverview, type Overview } from '@/api/overview';

// The overview of the building in the route (/buildings/:id), or of the demo's
// reference workbook; reloaded when the id changes. Pages show `error` and loading.
export function useOverview() {
  const route = useRoute();
  const overview = ref<Overview | null>(null);
  const error = ref<string | null>(null);
  watch(
    () => route.params.id,
    async (id) => {
      overview.value = null;
      error.value = null;
      try {
        overview.value = await fetchOverview(typeof id === 'string' ? Number(id) : undefined);
      } catch (e: unknown) {
        error.value = e instanceof Error ? e.message : String(e);
      }
    },
    { immediate: true },
  );
  return { overview, error };
}
