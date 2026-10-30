<template>
  <div class="checks">
    <p class="checks__summary">
      {{ kg.format(rowsRead) }} result rows read, one per bill of materials row.
      {{ plural(declaredWithoutResult, 'module is', 'modules are') }} declared with no result;
      {{ plural(resultWithoutDeclaration, 'module has', 'modules have') }} results that are not declared.
    </p>
    <ol class="checks__modules" aria-label="Life-cycle modules, in order">
      <li v-for="check in checks" :key="check.module" class="checks__module" :class="`checks__module--${state(check)}`">
        <span class="checks__name">{{ check.module }}</span>
        <span class="checks__state">{{ STATE_LABEL[state(check)] }}</span>
      </li>
    </ol>
  </div>
</template>

<script setup lang="ts">
import type { ModuleCheck } from '@/api/overview';
import { kg } from '@/format';

defineProps<{
  checks: ModuleCheck[];
  rowsRead: number;
  declaredWithoutResult: number;
  resultWithoutDeclaration: number;
}>();

type State = 'complete' | 'out' | 'declared_no_result' | 'result_not_declared';
const STATE_LABEL: Record<State, string> = {
  complete: 'Declared, has results',
  out: 'Not in scope',
  declared_no_result: 'Declared, no result',
  result_not_declared: 'Results, not declared',
};

const state = (check: ModuleCheck): State => {
  if (check.status !== 'ok') return check.status;
  return check.declared ? 'complete' : 'out';
};
const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;
</script>

<style scoped lang="scss">
@use '@/css/02-tokens' as tokens;

.checks {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-lg;
}

.checks__summary {
  margin: 0;
  max-width: 42rem;
}

.checks__modules {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(7.5rem, 1fr));
  gap: tokens.$spacing-sm;
  margin: 0;
  padding: 0;
  list-style: none;
}

.checks__module {
  display: flex;
  flex-direction: column;
  gap: tokens.$spacing-xxs;
  padding: tokens.$spacing-sm tokens.$spacing-md;
  border: tokens.$border-width solid tokens.$color-border;
  border-radius: tokens.$radius-default;
}

.checks__name {
  font-weight: tokens.$text-weight-bold;
}

.checks__state {
  font-size: tokens.$text-size-xs;
  color: tokens.$color-text-muted;
}

.checks__module--complete {
  background: tokens.$color-surface-muted;
}

.checks__module--out {
  border-style: dashed;
  border-color: tokens.$color-border-control;
}

// A mismatch: Orange Dark marks it; the text stays Black for contrast.
.checks__module--declared_no_result,
.checks__module--result_not_declared {
  border-left: tokens.$spacing-xs solid tokens.$color-status-warning;

  .checks__state {
    color: tokens.$color-text;
  }
}
</style>
