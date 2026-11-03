import { ref } from 'vue';
import { getJson } from '@/api/client';

// lmc-openbdf's meanings, keyed by the labels the app prints (GET /api/glossary).
// Loaded once for the whole app; until it arrives, or if it fails, names show plain.
interface Glossary {
  fields: Record<string, string>; // field code → description
  terms: Record<string, string>; // printed label, dashes as "-" → meaning
}

const glossary = ref<Glossary>({ fields: {}, terms: {} });
let loading: Promise<void> | null = null;

export const termKey = (label: string) => label.replace(/[–—]/g, '-').trim();

export function useGlossary() {
  loading ??= getJson<Glossary>('/glossary')
    .then((g) => {
      glossary.value = g;
    })
    .catch(() => undefined); // ponytail: tooltips are an aid; a failed load leaves plain names
  return glossary;
}
