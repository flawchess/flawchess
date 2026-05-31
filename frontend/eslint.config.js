import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist', 'dev-dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    rules: {
      // New in react-hooks 7.1.1 — codebase intentionally uses setState in effects
      // to derive state from server data and filter synchronisation. The patterns are
      // correct (each effect has a stable dependency array) and carry no cascading-
      // render risk at runtime. Re-evaluate if the affected hooks are refactored.
      'react-hooks/set-state-in-effect': 'off',
    },
  },
  // shadcn/ui components export variants alongside components — standard pattern
  {
    files: ['src/components/ui/**/*.{ts,tsx}'],
    rules: {
      'react-refresh/only-export-components': 'off',
    },
  },
  // Filter components co-export types, constants, and utility functions alongside
  // components (e.g. FilterState, DEFAULT_FILTERS, FILTER_DOT_FIELDS, CALENDAR_*).
  // react-refresh 0.5 narrowed allowConstantExport to primitive literals only, so
  // computed exports like new Date() and array constants now trigger the rule. The
  // pattern is intentional — these shared values live alongside the components that
  // define and own them.
  {
    files: ['src/components/filters/**/*.{ts,tsx}'],
    rules: {
      'react-refresh/only-export-components': 'off',
    },
  },
])
