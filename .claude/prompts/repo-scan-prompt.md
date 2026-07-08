# Phase 1 Prompt — Repository Scan & Documentation (Read-Only)

> Paste this into Claude Code, running inside the repo root.

---

You are doing a **read-only reconnaissance pass** on this repository. Do NOT create, edit, move, rename, or delete any file except the single report file described below. No refactors, no fixes, no "while I'm here" cleanups. This is discovery only — the reorganization itself will happen in a later, separate step after human review.

## What to scan

Walk the entire repository, excluding `.git`, `node_modules`, `venv`/`.venv`, `__pycache__`, build artifacts, and other standard ignorable directories. Use `git log` where useful to understand when files were last touched and by what kind of change.

## Output

Produce exactly one new file: `REPO_SCAN.md` at the repo root. Structure it with these sections:

### 1. Full file tree
Complete folder/file listing, annotated with size and last-modified date (from git).

### 2. Per-file purpose
For every source file, one line inferring its purpose from its content, imports, and usage elsewhere in the repo. Group this by current folder.

### 3. Pipeline-stage mapping
This project is organized around a processing pipeline. For every file, identify which pipeline stage it belongs to (e.g. data ingestion, preprocessing, model/training, evaluation, output/reporting, utilities/shared, or "unclear"). Present this as a stage → file list, not just file → stage, so we can see each stage's footprint at a glance.

### 4. Existing markdown docs audit
List every `.md` file currently in the repo. For each: what it currently claims/documents, and a flag — **accurate**, **outdated**, **duplicate of another file**, or **orphaned/unclear purpose**.

### 5. AI model references
Search the entire repo (code, configs, prompts, comments, docs — everywhere) for any string that names a specific AI model or version (e.g. `claude-...`, `gpt-...`, model IDs in config/env files, hardcoded model names in prompts). List every occurrence with file path + line number + the exact string found. This project's model choice has just been finalized, so we need the complete list of every place a model name is currently referenced in order to reconcile them all against the current choice.

### 6. Links / external resources
Search the entire repo for URLs (docs, README files, config files, code comments). List every occurrence with file path + line number + the URL itself, so each can be checked for validity/relevance later.

### 7. Clutter candidates
Flag, without deleting: duplicate files, files with no incoming references/imports anywhere in the repo, empty files, obvious scratch/temp/output files that look accidentally committed, and anything else that looks like clutter. Explain briefly why each is flagged.

### 8. Dependency notes
To the extent inferable, note which files/modules import or depend on which others — enough to understand what would break if a file were moved.

### 9. Proposed reorganization (proposal only, do not execute)
Sketch a possible folder structure organized by pipeline stage (e.g. numbered folders reflecting pipeline order), showing where each existing file would land. Mark this clearly as a **proposal for review**, not an action taken.

### 10. Open questions for the maintainer
Anything ambiguous you couldn't resolve on your own — unclear file purpose, conflicting docs, ambiguous model references, files you weren't confident how to classify.

---

Remember: this pass only produces `REPO_SCAN.md`. No other file in the repository should be touched.
