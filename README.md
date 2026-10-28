# Sala Propia

Perfil cinéfilo y recomendador a partir de Letterboxd (usuario `fmillag`). Es una web estática instalable (PWA) servida con GitHub Pages.

- `index.html`: la app.
- `sync-data.js`: lo que trae el feed RSS de Letterboxd. Lo reescribe `sync_letterboxd.py`.
- `base-keys.json`: películas del export original de Letterboxd, para saber qué es nuevo.
- `.github/workflows/sync.yml`: corre el sync todos los días y commitea si hubo cambios. Se puede lanzar a mano desde la pestaña Actions → Sync Letterboxd → Run workflow.

Sync local: `python sync_letterboxd.py fmillag`
