# Agamotto — Ilimi's internal intelligence layer

Named for the Eye of Agamotto: the thing that sees. This app is the
all-seeing internal platform for Ilimi's team — not a tenant-facing feature.
It exists so founders and engineers can understand how the product is really
being used, where schools are thriving or struggling, and how to position
Ilimi for the future.

**Scope discipline:** this app grows deliberately. Today it holds exactly one
thing — demo/lead capture from the marketing site. Everything below is
roadmap, not built. Resist folding half-finished analytics in under time
pressure; each piece lands whole.

## Roadmap (not yet built)

1. **Adoption & health** — schools signed up, active vs dormant, per-feature
   usage, churn-risk signals (last login, still taking attendance).
2. **Business metrics** — revenue per school, GH₵ collected via the platform,
   plan distribution, growth rate.
3. **Operational health** — SMS delivery + Arkesel cost, failed payments,
   error rates, slow endpoints.
4. **Lead pipeline** — demo requests, follow-up status, lead→signed-school
   conversion. (The one piece that exists today.)
5. **Cohort & behavioural analysis** — how usage evolves over a school's
   first term, what predicts renewal, which features correlate with retention.

## Non-negotiable principle: privacy & access control

Agamotto reads across every tenant's data, including children's records. Any
feature beyond aggregate lead data MUST:
- be restricted to Ilimi staff only (never a school admin),
- audit-log who viewed what,
- default to aggregation (counts, trends) rather than individual children's
  records — expose individual records only with a real, logged support reason.

Bake this in from each feature's first line, never bolt it on.