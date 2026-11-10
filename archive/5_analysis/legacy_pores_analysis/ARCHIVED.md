# ARCHIVED

This folder (formerly `legacy/pores_analysis/`) was archived on **2026-07-08**
during the repository reorganization (see `REORG_PLAN.md` §6 and
`REORG_EXECUTION_REPORT.md`).

- **Status**: archived, pending deletion in the next reorg/cleanup cycle.
- **Why kept for now, not deleted immediately**: `REORG_PLAN.md` §6 confirmed
  zero *internal* runtime dependency — nothing in `05_evaluation/psd/`
  (the live PSD diagnostics pipeline) imports from this package, and this
  package's own internal imports are self-contained. That re-verification
  could not rule out an external, personal script outside this repo still
  calling into it, so outright deletion was deferred pending the
  maintainer's confirmation.
- **Superseded by**: `05_evaluation/psd/psd_diagnostics_core.py` and
  `05_evaluation/psd/psd_topology_metrics.py`, which are the live,
  independently-written implementations of the same class of metrics
  (Euler characteristic, connectivity density/probability, anisotropy,
  tortuosity) used by the current pipeline.
- **Do not** base new implementations on this folder or modify it as part
  of ongoing pipeline work.
