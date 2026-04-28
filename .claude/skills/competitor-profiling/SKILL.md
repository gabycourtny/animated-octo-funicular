---
name: competitor-profiling
description: Creates structured competitor profiles by combining live website scraping with SEO and market intelligence data, producing comparable markdown documents for each competitor. Covers three phases—site scraping, SEO intelligence, and synthesis—with timestamped data storage for auditing and reuse.
---

# Competitor Profiling Guide

This document provides a comprehensive framework for researching and analyzing competitors through URL-based profiling.

## Core Purpose

The system creates structured competitor profiles by combining live website scraping with SEO and market intelligence data, producing comparable markdown documents for each competitor analyzed.

## Key Workflow Steps

**Phase 1 (Site Scraping)**: Map competitor sites using Firecrawl, then scrape key pages—homepage, pricing, features, about, customers, integrations, and changelog—extracting positioning, capabilities, pricing tiers, and product direction signals.

**Phase 2 (SEO Intelligence)**: Use DataForSEO tools to gather domain authority, backlink counts, organic keyword rankings, estimated traffic, and competitive positioning data.

**Phase 3 (Synthesis)**: Combine scraped content with quantitative metrics to build comprehensive profiles, cross-referencing claims against available data.

## Output Structure

Each competitor receives an individual markdown profile containing an at-a-glance table, positioning analysis, product details, pricing breakdown, customer information, SEO metrics, strengths/weaknesses assessment, and competitive implications.

A summary document compares all profiled competitors side-by-side with a landscape overview, positioning map, and strategic observations.

## Data Storage

Raw data is preserved in timestamped directories (`competitor-profiles/raw/<slug>/<YYYY-MM-DD>/`) organized by data type: scrapes, SEO metrics, and reviews—enabling auditing and re-use without repeating API calls.

## Approach Selection

**Quick scans** cover homepage and pricing pages with basic SEO overview. **Deep profiles** include all pages, review sites, backlink analysis, and technology stack details. Quick scans are default for multiple competitors; deep profiles suit 3 or fewer competitors.
