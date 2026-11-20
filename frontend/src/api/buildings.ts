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

// Every reject of one code in one line, most frequent first: the draft badge lists them.
export interface RejectSummary {
  code: string;
  count: number;
  message: string;
  what_to_do: string;
}

export interface BuildingSummary {
  id: number;
  file_name: string;
  uploaded_at: string;
  gbdi_id?: string | null; // the generated project id (org#108)
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
  project_reference: string | null; // the source publication, to cite (org#115)
  project_doi: string | null;
  blocked: ('carbon' | 'materials')[]; // the parts its rejects block
  rejects: string[];
  reject_summary: RejectSummary[];
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
  system_boundary: string | null; // as General Information declares it
  whole_life_per_m2: number | null;
  upfront_per_m2: number | null;
  module_d1_per_m2: number | null;
  has_module_d: boolean; // a non-zero D1 or D2 result; a declared D flag alone does not count
  module_d_per_m2: number | null; // D1 + D2, outside the total; null without module D or without a floor area
  project_reference: string | null; // the source publication (org#115)
  project_doi: string | null;
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
  // The owner's rule (org#94): which case, the stages each building covers, and the
  // scope the figures above apply. Stage lists hold labels, "A1–A3".
  case: CompareCase;
  applied_scope: CompareScope; // common: every figure on the common stages, merged charts
  covered_a: string[];
  covered_b: string[];
  common_stages: string[];
  left_out: LeftOut[];
  stages_a: string[]; // the stages a's whole-life figure stands for
  stages_b: string[];
  upfront_stages: string[];
  ratio_stages: string[] | null; // null: the totals cover different stages, no ratio sentence
}

export type CompareCase = 'methods_differ' | 'no_common_stages' | 'same_stages' | 'different_stages';
export type CompareScope = 'common' | 'own';

export interface LeftOut {
  stage: string;
  not_covered_by: 'a' | 'b';
  value: number | null; // kg CO₂e per m² of the building that covers it
}

export const fetchBuildings = () => getJson<BuildingSummary[]>('/buildings');
export const fetchBuilding = (id: number) => getJson<BuildingSummary>(`/buildings/${id}`);
export const deleteBuilding = (id: number) => deleteJson(`/buildings/${id}`);
export const fetchDraft = (id: number) => getJson<DraftView>(`/buildings/${id}/draft`);
export const fetchComparison = (a: number, b: number, scope: CompareScope) =>
  getJson<Comparison>(`/buildings/compare?a=${a}&b=${b}&scope=${scope}`);

export function uploadBuilding(file: File, draft = false) {
  const form = new FormData();
  form.append('file', file);
  return postForm<BuildingSummary>(`/buildings${draft ? '?draft=true' : ''}`, form);
}

// The building's short name: the workbook's file name, as the COLA set names them.
export const code = (b: { file_name: string }) => b.file_name.replace(/\.xlsx$/i, '');
