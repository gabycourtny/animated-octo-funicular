---
name: ad-creative
description: Generates and iterates high-performing ad creative across platforms including Google Ads, Meta, LinkedIn, TikTok, and Twitter/X, handling headlines, descriptions, and full ad variations at scale. Supports both creating fresh creative from scratch and iterating on existing creative using performance data.
---

# Ad Creative Agent Documentation

## Overview
This agent specializes in generating and iterating high-performing ad creative across platforms like Google Ads, Meta, LinkedIn, TikTok, and Twitter/X. It handles headlines, descriptions, primary text, and full ad variations at scale.

## Key Capabilities

**Generation modes:**
- Create fresh ad creative from scratch based on product context and audience insights
- Iterate existing creative using performance data to identify winning patterns

**Platform support with character limits:**
- Google Ads RSAs: 30-char headlines (up to 15), 90-char descriptions (up to 4)
- Meta: 125-char primary text, 40-char headlines
- LinkedIn: 150-char intro text, 70-char headlines
- TikTok: 80-char ad text
- Twitter/X: 280-char tweets, 70-char headlines

## Workflow Steps

1. **Define angles** — Establish 3-5 distinct motivations (pain points, outcomes, social proof, curiosity, etc.)
2. **Generate variations** — Create multiple options per angle with different word choice, specificity, and tone
3. **Validate specs** — Verify all copy stays within platform character limits
4. **Organize for upload** — Structure as CSV or formatted output matching platform requirements

## Quality Standards

Strong creative features specific benefits ("Cut reporting time 75%"), active voice, and numbers when possible. Descriptions should complement rather than repeat headlines, adding proof points or handling objections.

## Integration
The agent can pull performance data from advertising platforms via tool integrations, analyze top/bottom performers for patterns, and generate new variations that double down on winners while testing unexplored angles.
