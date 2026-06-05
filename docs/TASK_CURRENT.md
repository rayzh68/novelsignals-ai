# Current Task

Phase: Post MVP Expansion

---

## Priority

1. Verify Market Signal Quality

2. Remove Weak Signals

Examples:

- after
- life
- night
- alone

3. Build SEO Asset Package

Outputs:

- seo_title
- seo_description
- seo_keywords
- schema_jsonld
- faq
- internal_links

4. Build Creative Asset Package

Outputs:

- hero_image_prompt
- og_image_prompt
- social_post_prompt
- youtube_prompt

5. Build Unified Pipeline

Target:

python -m novelsignals_ai all

Pipeline:

discover
collect
data
site
seo
creative
export

---

## Constraints

Do not increase file count unnecessarily.

Prefer extending existing modules.

Preserve platform ranking order.

Respect platform ranking logic.

Use NovelSignals ranking only for NovelSignals generated rankings.

---

# Current Task Update - 2026-06-05

## Completed

- Git repository initialized.
- First commit completed.
- GitHub repository pushed.
- v0.4 tag created.
- Discovery V2 architecture validated.
- Active source of truth confirmed:
  - data/input/book_metadata
  - data/current/catalog

## Important Decision

data/output/book_metadata is legacy output.

Do not use it as the active pipeline source.

Do not spend time fixing batch_pipeline.py unless legacy cleanup becomes a dedicated task.

## Current Priority

Platform Seed Expansion.

Goal:

Increase ranking/market-entry discovery sources, while keeping Discovery generic and avoiding hardcoded genre/topic logic.

