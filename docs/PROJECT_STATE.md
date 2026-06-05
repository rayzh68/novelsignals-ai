# NovelSignals AI - Project State

Date: 2026-06-04

Version: V0.3

Stage: Market Intelligence MVP

---

## Completed

### Discovery

- Public URL Discovery
- URL Cleaning
- Platform Discovery

### Metadata

- Metadata Collection
- Metadata Normalization
- Platform Metadata Storage

### Catalog

- Unified Catalog
- Genre Statistics
- Keyword Statistics
- Rankings

### Market Signals

- Topic Candidates
- Genre Rankings
- Market Signals

### Content Bundle

- Home Page
- Book Detail Pages
- Ranking Pages
- Topic Pages

---

## Current Metrics

Books: 102

Genres: 22

Keywords: 261

Market Signals: 58

Metadata Grades

A: 37
B: 64
C: 1

Generated Pages: 130

---

## Important Decisions

Platform rankings preserve platform order.

NovelSignals rankings are independent.

Topic Pages come from Market Signals.

System exports structured data packages only.

Website rendering is out of scope.

---

## Current Pipeline

Discovery
→ Metadata
→ Catalog
→ Market Signals
→ Content Bundle

Status: Operational

---

# 2026-06-05 Architecture Validation

## Validation Results

Discovery URLs: 1470

Raw Metadata: 104

Input Metadata: 106

Catalog Books: 102

## Confirmed Active Pipeline

discover
→ normalize_metadata
→ catalog_builder
→ asset_generator
→ content_asset_generator

Confirmed via __main__.py.

## Legacy Components

batch_pipeline.py

output/book_metadata

Status:

Legacy only.

Not referenced by active pipeline.

No action required.

## Current Source Of Truth

data/input/book_metadata

data/current/catalog

## Decisions

Discovery V2 complete.

Do not modify batch_pipeline.py.

Do not use output/book_metadata as source data.

Catalog generation validated.

## Next Priority

Platform Ranking Intelligence

Research:

- GoodNovel ranking structure
- Dreame ranking structure
- WebNovel ranking structure

Goal:

NovelSignals rankings should respect platform rankings instead of replacing them.

