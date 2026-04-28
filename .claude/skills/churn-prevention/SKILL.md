---
name: churn-prevention
description: Covers strategies for reducing both voluntary churn (cancel flows, exit surveys, save offers) and involuntary churn (dunning, failed payment recovery), with benchmarks, recommended tools, and cohort analysis guidance. Provides a structured cancel flow design and dunning sequence framework.
---

# Churn Prevention Guide

This comprehensive resource covers strategies for reducing both voluntary churn (customer-initiated cancellations) and involuntary churn (failed payments).

## Core Framework

The guide structures churn prevention around two main approaches:

**Voluntary Churn** — Managed through cancel flows with exit surveys, dynamic save offers, and confirmation steps. The key principle is matching offers to cancellation reasons: discounts for price sensitivity, pauses for low engagement, feature roadmaps for product gaps.

**Involuntary Churn** — Addressed via dunning strategies including smart retry logic, pre-failure card alerts, and email recovery sequences. This represents 30-50% of total churn but has higher recovery potential.

## Cancel Flow Design

A structured exit experience follows this sequence:
- Exit survey identifying cancellation reason
- Targeted offer based on that reason
- Clear confirmation messaging
- Post-cancel reactivation pathway

The guide emphasizes that "a discount won't save someone who isn't using the product. A feature roadmap won't save someone who can't afford it."

## Key Metrics

Success measurement focuses on:
- Monthly churn rates (targets: <5% B2C, <2% B2B)
- Cancel flow save rates (25-35% benchmark)
- Dunning recovery rates (50-60% target)
- Cohort analysis by acquisition channel, plan type, and tenure

## Implementation Tools

Recommended platforms include Churnkey, ProsperStack, and Raaft for cancel flows, plus native dunning capabilities in Stripe, Chargebee, Paddle, and Recurly.

The resource links to related skills covering email sequences, upgrade paywalls, and analytics tracking.
