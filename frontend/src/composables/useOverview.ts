import { onMounted, ref } from 'vue';
import { fetchOverview, type Overview } from '@/api/overview';

// One load per page; the pages show `error` and the loading state themselves.
export function useOverview() {
  const overview = ref<Overview | null>(null);
  const error = ref<string | null>(null);
  onMounted(async () => {
    try {
      overview.value = await fetchOverview();
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : String(e);
    }
  });
  return { overview, error };
}
