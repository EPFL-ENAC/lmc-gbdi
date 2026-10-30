import { deleteJson, getJson, postForm } from './client';
import type { Benchmark } from './overview';

// Mirrors backend/app/buildings/schemas.py. Per m² means per m² of gross floor area.

export interface Finding {
  code: string;
  severity: 'Info' | 'Warning' | 'Reject';
  sheet: string | null;
  row: number | null;
  message: string;
}

export interface BuildingSummary {
  id: number;
  file_name: string;
  uploaded_at: string;
  findings: number;
  project_name: string | null;
  country: string | null;
  gross_floor_area_m2: number | null;
  rows_read: number;
  whole_life: number;
  whole_life_per_m2: number | null;
  stages_per_m2: Record<string, number> | null;
  leti_band: string | null;
}

export interface Rejection {
  message: string;
  findings: Finding[];
}

export interface ComparedBuilding {
  id: number;
  file_name: string;
  project_name: string | null;
  country: string | null;
  gross_floor_area_m2: number | null;
  rows_read: number;
  whole_life_per_m2: number | null;
  upfront_per_m2: number | null;
  module_d1_per_m2: number | null;
  benchmarks: Benchmark[];
}

export interface ComparedRow {
  label: string;
  a: number | null;
  b: number | null;
}

export interface Comparison {
  a: ComparedBuilding;
  b: ComparedBuilding;
  ratio: number | null;
  stages: ComparedRow[];
  elements: ComparedRow[];
  material_carbon: ComparedRow[];
  material_mass: ComparedRow[];
}

export const fetchBuildings = () => getJson<BuildingSummary[]>('/buildings');
export const fetchBuilding = (id: number) => getJson<BuildingSummary>(`/buildings/${id}`);
export const deleteBuilding = (id: number) => deleteJson(`/buildings/${id}`);
export const fetchComparison = (a: number, b: number) => getJson<Comparison>(`/buildings/compare?a=${a}&b=${b}`);

export function uploadBuilding(file: File) {
  const form = new FormData();
  form.append('file', file);
  return postForm<BuildingSummary>('/buildings', form);
}

// The building's short name: the workbook's file name, as the COLA set names them.
export const code = (b: { file_name: string }) => b.file_name.replace(/\.xlsx$/i, '');
