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
  scope: string; // the stages the totals cover, e.g. "A–C · whole life"
  upfront: number;
  upfront_share: number;
  per_m2_useful: number | null;
  per_m2_gross: number | null;
  per_m2_useful_per_year: number | null; // as the COLA sheet
  per_m2_gross_per_year: number | null; // the declared basis, 1 m² GFA / year
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
  share: number; // of the whole-life GWP
  mass_kg: number;
  share_of_mass: number | null; // of the total mass; null when no mass is declared
}

export interface ElementMaterial {
  material: string;
  epd_product: string;
  mass_kg: number;
  share: number | null; // of the element's mass; null when the element has none
}

// One element bar and the mass of the materials it holds.
export interface ElementMaterials {
  element: string;
  mass_kg: number;
  materials: ElementMaterial[]; // the 5 heaviest
  other: ElementMaterial | null; // every other material as one row
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

// What every absolute figure is divided by (backend `Basis`).
export type Basis = 'total' | 'gfa' | 'ufa' | 'gfa_year';

export interface BasisOption {
  key: Basis;
  label: string;
  available: boolean;
  reason: string | null; // why the building cannot serve it
}

// The unit each kind of figure reads in, on the overview's basis.
export interface Units {
  basis: Basis;
  carbon: string;
  mass: string; // by area only, never per year
  time: string; // the Time section's carbon, by area only
  intensity: string; // carbon over mass
}

// The Time section's figures, on the basis's area but never per year.
export interface TimeFigures {
  stages: StageTotal[];
  upfront: number;
  use_per_year: number | null; // B1–B8 spread evenly over the study period
  module_d1: number;
}

// The names the element and material figures go by (backend `Naming`).
export type Naming = 'openbdf' | 'custom';

// Every figure named by element or material, under one naming.
export interface NamingView {
  elements: ElementTotal[];
  other_classified: ElementTotal;
  not_classified: ElementTotal;
  element_stages: ElementStages[];
  material_hotspots: MaterialHotspot[];
  mass_hotspots: MassHotspot[];
  materials: MaterialHotspot[];
  mass_other_share: number;
  element_materials: ElementMaterials[];
}

export interface Overview {
  project: ProjectInfo;
  project_fields: ProjectField[];
  title_block: ProjectField[]; // the 14 the Overview heads with, in #97's order
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
  materials: MaterialHotspot[]; // every material, by whole-life carbon
  total_mass_kg: number;
  mass_other_share: number;
  material_classes: MaterialClassTotal[];
  namings: Record<Naming, NamingView>; // the top-level element and material fields are openbdf and custom
  time: TimeFigures;
  units: Units;
  bases: BasisOption[]; // every basis, with whether this building can serve it
  data_type_weighting: 'gwp_fossil_a1_a3' | 'mass' | 'not_computed';
  data_types: DataTypeShare[];
}

export const fetchOverview = (id: number, basis: Basis) =>
  getJson<Overview>(`/buildings/${id}/overview?basis=${basis}`);
