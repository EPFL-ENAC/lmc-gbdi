// Number formats in the reader's locale; the app has no i18n yet.
export const kg = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });
export const one = new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 });
export const two = new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 });
export const three = new Intl.NumberFormat(undefined, { minimumFractionDigits: 3, maximumFractionDigits: 3 });
export const percent = new Intl.NumberFormat(undefined, { style: 'percent', maximumFractionDigits: 1 });

export const figure = (value: number | null, format: Intl.NumberFormat) =>
  value === null ? 'not declared' : format.format(value);

export const materialName = (material: string) => material || 'No material name';

// How the data type profile is weighted, as a sentence.
export const WEIGHTING: Record<'gwp_fossil_a1_a3' | 'mass' | 'not_computed', string> = {
  gwp_fossil_a1_a3: 'Weighted by GWP fossil A1–A3.',
  mass: 'Weighted by mass: no GWP fossil A1–A3 is declared.',
  not_computed: 'Not computed: neither GWP fossil A1–A3 nor mass is declared.',
};
