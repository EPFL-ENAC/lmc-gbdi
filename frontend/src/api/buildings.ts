import { deleteJson, getJson, postForm } from './client';
import type { ProjectField } from './overview';

// Mirrors backend/app/buildings/schemas.py. Per m² means per m² of gross floor area.

export interface Finding {
  code: string;
  severity: 'Info' | 'Warning' | 'Reject';
  sheet: string | null;
  row: number | null;
  message: string;
  count: number; // above 1, the entry stands for the rest of its code and sheet
}

// The findings of one code on one sheet, rejects first, then the most frequent.
export interface FindingGroup {
  code: string;
  severity: Finding['severity'];
  sheet: string | null;
  count: number;
  examples: Finding[]; // the first ones, then one entry for the rest
}

export interface BuildingSummary {
  id: number;
  file_name: string;
  uploaded_at: string;
  findings: number;
  project_name: string | null;
  country: string | null;
  gross_floor_area_m2: number | null;
  useful_floor_area_m2: number | null;
  study_period_years: number | null;
  rows_read: number;
  whole_life: number | null; // null for a draft whose rejects block carbon
  whole_life_per_m2: number | null;
  stages_per_m2: Record<string, number> | null;
  scope: string | null; // of whole_life; null with it
  lcia_methodology: string | null; // as General Information declares it
  draft: boolean; // stored despite reject findings
  blocked: ('carbon' | 'materials')[]; // the parts its rejects block
  rejects: string[];
}

// A draft is visible but never counted, and one without carbon never compared.
export const noCarbon = (b: { blocked: string[] }) => b.blocked.includes('carbon');

export interface DraftView {
  project_fields: ProjectField[];
  rows_read: number;
  rejects: Finding[];
  findings_count: number; // everything openbdf reported, warnings included
  finding_groups: FindingGroup[];
  blocked: ('carbon' | 'materials')[];
  gross_floor_area_m2: number | null;
  total_mass_kg: number | null;
  material_classes: { label: string; mass_kg: number }[];
}

export interface Rejection {
  message: string;
  findings_count: number;
  finding_groups: FindingGroup[];
}

export interface ComparedBuilding {
  id: number;
  file_name: string;
  project_name: string | null;
  country: string | null;
  gross_floor_area_m2: number | null;
  rows_read: number;
  scope: string;
  lcia_methodology: string | null;
  whole_life_per_m2: number | null;
  upfront_per_m2: number | null;
  module_d1_per_m2: number | null;
}

export interface ComparedRow {
  label: string;
  a: number | null;
  b: number | null;
}

export interface Comparison {
  a: ComparedBuilding;
  b: ComparedBuilding;
  comparability: 'same_method' | 'methods_differ' | 'method_not_declared'; // of their LCIA methods
  method_note: string; // why two LCIA methods do not compare one to one
  ratio: number | null;
  stages: ComparedRow[];
  elements: ComparedRow[];
  material_carbon: ComparedRow[];
  material_mass: ComparedRow[];
}

export const fetchBuildings = () => getJson<BuildingSummary[]>('/buildings');
export const fetchBuilding = (id: number) => getJson<BuildingSummary>(`/buildings/${id}`);
export const deleteBuilding = (id: number) => deleteJson(`/buildings/${id}`);
export const fetchDraft = (id: number) => getJson<DraftView>(`/buildings/${id}/draft`);
export const fetchComparison = (a: number, b: number) => getJson<Comparison>(`/buildings/compare?a=${a}&b=${b}`);

export function uploadBuilding(file: File, draft = false) {
  const form = new FormData();
  form.append('file', file);
  return postForm<BuildingSummary>(`/buildings${draft ? '?draft=true' : ''}`, form);
}

// The building's short name: the workbook's file name, as the COLA set names them.
export const code = (b: { file_name: string }) => b.file_name.replace(/\.xlsx$/i, '');
