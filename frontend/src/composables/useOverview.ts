import { ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { fetchOverview, type Overview } from '@/api/overview';

// The overview of the building in the route (/buildings/:id), reloaded when the id
// changes. Pages show `error` and the loading state themselves.
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
        overview.value = await fetchOverview(Number(id));
      } catch (e: unknown) {
        error.value = e instanceof Error ? e.message : String(e);
      }
    },
    { immediate: true },
  );
  return { overview, error };
}
