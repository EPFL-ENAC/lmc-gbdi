import type { ComparedRow } from '@/api/buildings';
import type { Overview } from '@/api/overview';
import type { NamedOverview } from '@/composables/useOverview';

// Two buildings only compare per m² of gross floor area; null when it is not declared.
export const perM2 = (o: Overview, value: number) => {
  const area = o.project.gross_floor_area_m2;
  return area ? value / area : null;
};

// Rows of both buildings matched by label, in A's order then B's leftovers. A label one
// building lacks reads 0 for it (it has none of that), per m² like the rest.
export function pairRows<O extends Overview, T>(a: O, b: O, pick: (o: O) => T[], label: (row: T) => string, value: (row: T) => number) {
  const byLabel = (o: O) => new Map(pick(o).map((row) => [label(row), value(row)]));
  const ma = byLabel(a);
  const mb = byLabel(b);
  const labels = [...new Set([...ma.keys(), ...mb.keys()])];
  return labels.map<ComparedRow>((l) => ({
    label: l,
    a: perM2(a, ma.get(l) ?? 0),
    b: perM2(b, mb.get(l) ?? 0),
  }));
}

// One naming rule on every compare page: "Iewan (NL-23)" in words, the code alone in
// chart legends (o.code).
export const projectName = (o: NamedOverview) => `${o.project.project_name ?? 'Unnamed project'} (${o.code})`;

// True when neither building declares any data type: say it in one sentence instead of
// a chart of zeros.
export const noDataTypes = (...os: Overview[]) =>
  os.every((o) => o.data_types.every((d) => d.key === 'undeclared' || d.share === 0));

export const NO_DATA_TYPES_SENTENCE = 'Neither building declares the data type of its materials yet.';
