import { getJson } from './client';

// Mirrors backend/app/overview/schemas.py. GWP in kg CO₂ eq, mass in kg, shares 0–1.

export interface ProjectInfo {
  project_id: string | null;
  project_name: string | null;
  country: string | null;
  gross_floor_area_m2: number | null;
  useful_floor_area_m2: number | null;
  reference_study_period_years: number | null;
  lca_database: string | null;
  lcia_methodology: string | null;
  system_boundary: string | null;
}

export interface Headline {
  whole_life: number;
  upfront: number;
  upfront_share: number;
  per_m2_useful: number | null;
  per_m2_gross: number | null;
  per_m2_useful_per_year: number | null;
  module_d1: number;
  module_d2: number;
}

export interface StageTotal {
  key: string;
  label: string;
  gwp: number;
  share: number;
}

export interface ElementTotal {
  element: string;
  gwp: number;
  share: number;
}

export interface ElementStages {
  element: string;
  gwp_by_stage: Record<string, number>;
  dominant_stage: string;
  dominant_share: number;
}

export interface MaterialHotspot {
  material: string; // "" when the bill of materials names no material
  epd_product: string;
  gwp: number;
  mass_kg: number;
  share: number;
  share_of_mass: number | null; // null when no mass is declared
  gwp_per_kg: number | null;
  gwp_by_stage: Record<string, number>;
}

export interface MassHotspot {
  material: string;
  epd_product: string;
  mass_kg: number;
  share_of_mass: number;
  gwp: number;
  share: number; // of the whole-life GWP
}

export interface MaterialClassTotal {
  label: string; // OpenBDF material class, "4.2 Concrete"
  gwp: number;
  mass_kg: number;
}

export interface DataTypeShare {
  key: string;
  label: string;
  share: number;
}

export interface ProjectField {
  code: string;
  label: string;
  group: string;
  value: string | null; // null: General Information leaves it blank
}

export interface ModuleCheck {
  module: string;
  declared: boolean;
  has_result: boolean;
  status: 'ok' | 'declared_no_result' | 'result_not_declared';
}

export interface BenchmarkBand {
  label: string;
  upper: number | null; // kg CO₂e per m²; null for the open-ended last band
}

export interface Benchmark {
  key: string;
  name: string;
  source: string;
  source_url: string;
  scope: string;
  basis: 'per_m2_gross' | 'per_m2_useful';
  value: number | null;
  bands: BenchmarkBand[];
  band: string | null;
}

export interface Overview {
  project: ProjectInfo;
  project_fields: ProjectField[];
  rows_read: number;
  module_checks: ModuleCheck[];
  modules_declared_without_result: number;
  modules_with_undeclared_result: number;
  headline: Headline;
  stages: StageTotal[];
  elements: ElementTotal[];
  other_classified: ElementTotal;
  not_classified: ElementTotal;
  element_stages: ElementStages[];
  material_hotspots: MaterialHotspot[];
  mass_hotspots: MassHotspot[];
  total_mass_kg: number;
  mass_other_share: number;
  material_classes: MaterialClassTotal[];
  use_per_year: number | null;
  benchmarks: Benchmark[];
  data_type_weighting: 'gwp_fossil_a1_a3' | 'mass' | 'not_computed';
  data_types: DataTypeShare[];
}

export const fetchOverview = (id: number) => getJson<Overview>(`/buildings/${id}/overview`);
