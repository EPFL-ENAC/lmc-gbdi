import { computed, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ApiError } from '@/api/client';
import { fetchOverview, type Basis, type Overview } from '@/api/overview';

const BASES: Basis[] = ['total', 'gfa', 'ufa', 'gfa_year'];

// The overview of the route's building (/buildings/:id) on the chosen basis, reloaded
// when either changes. The basis lives in the URL (?basis=, left out for the total), so
// a reload, a shared link and the building bar keep it. Pages show `error` and the
// loading state themselves.
export function useOverview() {
  const route = useRoute();
  const router = useRouter();
  const basis = computed<Basis>({
    get: () => BASES.find((b) => b === route.query.basis) ?? 'total',
    set: (b) => void router.replace({ query: { ...route.query, basis: b === 'total' ? undefined : b } }),
  });
  const overview = ref<Overview | null>(null);
  const error = ref<string | null>(null);
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
        if (!current()) return;
        // ponytail: only the backend knows which bases a building serves (422 otherwise),
        // so a basis carried over from another building costs one failed request, then
        // the total. Ask first when the building list says what each one serves.
        if (e instanceof ApiError && e.status === 422 && b !== 'total') basis.value = 'total';
        else error.value = e instanceof Error ? e.message : String(e);
      }
    },
    { immediate: true },
  );
  return { overview, error, basis };
}
