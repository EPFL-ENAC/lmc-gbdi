import type { ComparedRow } from '@/api/buildings';
import type { Overview } from '@/api/overview';

// Two buildings only compare per m² of gross floor area; null when it is not declared.
export const perM2 = (o: Overview, value: number) => {
  const area = o.project.gross_floor_area_m2;
  return area ? value / area : null;
};

// Rows of both buildings matched by label, in A's order then B's leftovers. A label one
// building lacks reads 0 for it (it has none of that), per m² like the rest.
export function pairRows<T>(a: Overview, b: Overview, pick: (o: Overview) => T[], label: (row: T) => string, value: (row: T) => number) {
  const byLabel = (o: Overview) => new Map(pick(o).map((row) => [label(row), value(row)]));
  const ma = byLabel(a);
  const mb = byLabel(b);
  const labels = [...new Set([...ma.keys(), ...mb.keys()])];
  return labels.map<ComparedRow>((l) => ({
    label: l,
    a: perM2(a, ma.get(l) ?? 0),
    b: perM2(b, mb.get(l) ?? 0),
  }));
}

// The building's name in a heading.
export const projectName = (o: Overview) => o.project.project_name ?? 'Unnamed project';
