import { ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { fetchOverview, type Overview } from '@/api/overview';

// The overview of the route's building (/buildings/:id), reloaded when its id changes.
// Pages show `error` and the loading state themselves.
export function useOverview() {
  const route = useRoute();
  const overview = ref<Overview | null>(null);
  const error = ref<string | null>(null);
  watch(
    () => route.params.id,
    async (id) => {
      overview.value = null;
      error.value = null;
      if (id === undefined) return;
      // Switching fast, a slower earlier reply must not overwrite the current one.
      const current = () => route.params.id === id;
      try {
        const o = await fetchOverview(Number(id));
        if (current()) overview.value = o;
      } catch (e: unknown) {
        if (current()) error.value = e instanceof Error ? e.message : String(e);
      }
    },
    { immediate: true },
  );
  return { overview, error };
}
