# Shared model store and upstream sync

## Completed

- Shared store: `/mnt/A4C45B32C45B2C87/ai-models`.
- 300 old paths migrated to 257 SHA-256 objects; full verify GREEN.
- 13 Hugging Face cache roots merged; all former roots are symlinks.
- GitHub fork created: `nnnet/Hy-Nomas`.
- `origin` points to the fork; `upstream` points to Tencent and has push disabled.
- Local `main`, `integration/local-runtime`, `origin/main` and `upstream/main`
  are based on `36e2bdb0f91455d97e4dbd8e64af0129707cecdf`.
- `model-store-check`, `compose-config`, `models-ensure`, `upstream-check`,
  `spec-coverage` and strict OpenSpec validation are GREEN.
- Fresh-upstream API and web images build successfully.
- Compose starts and survives a real restart with the worker returning `ready`.
- Post-restart smoke, all 13 BDD scenarios, spec coverage and strict OpenSpec
  validation are GREEN.
- Runtime data, generated media, caches and `.serena` are excluded from the
  source wave.
