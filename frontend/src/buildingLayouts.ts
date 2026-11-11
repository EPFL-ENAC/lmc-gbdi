// One view per building (globalbuildingdatainitiative/org#97); the design demo's other
// layouts are in git history.
// /buildings/8, and /buildings/8/compare/9 when a second building is set beside it.
export const buildingPath = (id: number, other: number | null = null) =>
  `/buildings/${id}${other === null ? '' : `/compare/${other}`}`;
