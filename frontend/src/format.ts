import type { Units } from '@/api/overview';

// Number formats in the reader's locale; the app has no i18n yet.
export const NOT_DECLARED = 'not declared';
export const kg = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });
export const three = new Intl.NumberFormat(undefined, { minimumFractionDigits: 3, maximumFractionDigits: 3 });
export const percent = new Intl.NumberFormat(undefined, { style: 'percent', maximumFractionDigits: 1 });

// A total reads in whole kilograms. Per m² (and year) keeps two decimals, or three
// significant digits when that says more (0.0042, not 0).
const perArea = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 2,
  maximumSignificantDigits: 3,
  roundingPriority: 'morePrecision',
});
export const amount = (units: Units) => (units.basis === 'total' ? kg : perArea);

export const figure = (value: number | null, format: Intl.NumberFormat) =>
  value === null ? NOT_DECLARED : format.format(value);

export const materialName = (material: string) => material || 'No material name';

// How the data type profile is weighted, as a sentence.
export const WEIGHTING: Record<'gwp_fossil_a1_a3' | 'mass' | 'not_computed', string> = {
  gwp_fossil_a1_a3: 'Weighted by GWP fossil A1–A3.',
  mass: 'Weighted by mass: no GWP fossil A1–A3 is declared.',
  not_computed: 'Not computed: neither GWP fossil A1–A3 nor mass is declared.',
};

// A General Information value as a reader should see it: numbers in the reader's locale
// ("2865.0000" reads 2,865), blanks as not declared.
export const fieldText = (value: string | null) => {
  if (value === null || value.trim() === '') return NOT_DECLARED;
  const n = Number(value);
  return Number.isFinite(n) ? kg.format(n) : value;
};
