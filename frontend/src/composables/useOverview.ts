import { ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { fetchOverview, type Basis, type Overview } from '@/api/overview';

// The overview of the route's building (/buildings/:id) on the chosen basis, reloaded
// when either changes. Pages show `error` and the loading state themselves.
export function useOverview() {
  const route = useRoute();
  const basis = ref<Basis>('total');
  const overview = ref<Overview | null>(null);
  const error = ref<string | null>(null);
  // ponytail: a new building starts on its total, since the last basis may be one it
  // cannot serve; keep the basis across buildings when the list says what each serves.
  watch(
    () => route.params.id,
    () => {
      basis.value = 'total';
    },
  );
  watch(
    [() => route.params.id, basis],
    async ([id, b], previous) => {
      if (id !== previous?.[0]) overview.value = null; // a basis change keeps the page
      error.value = null;
      if (id === undefined) return;
      // Switching fast, a slower earlier reply must not overwrite the current one.
      const current = () => route.params.id === id && basis.value === b;
      try {
        const o = await fetchOverview(Number(id), b);
        if (current()) overview.value = o;
      } catch (e: unknown) {
        if (current()) error.value = e instanceof Error ? e.message : String(e);
      }
    },
    { immediate: true },
  );
  return { overview, error, basis };
}
