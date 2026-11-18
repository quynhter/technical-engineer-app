// Core ESLint rules only. No automatic formatting or UI dependencies.
export default [
  {ignores: ['**/node_modules/**', 'db/**', 'app/itd/web_assets/design.js']},
  {
    files: ['app/frontend/**/*.{js,jsx,mjs}', 'app/itd/web_assets/*.js', 'app/itd/*.mjs'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      parserOptions: {ecmaFeatures: {jsx: true}},
    },
    rules: {
      'constructor-super': 'error',
      'no-debugger': 'error',
      'no-dupe-args': 'error',
      'no-dupe-keys': 'error',
      'no-unreachable': 'error',
      'valid-typeof': 'error',
    },
  },
  {
    files: ['app/itd/web_assets/*.js'],
    languageOptions: {sourceType: 'script'},
  },
];
