# Security Remediation Flow — Build Specification

Traceable remediation from a security finding to a verified production fix, across every
affected repository of every affected application.

**Scale:** ~700 applications, ~7,000 repositories
**Finding sources:** AI-based discovery, SAST, SCA, image and infrastructure scanning
**Human decisions:** three
**Target:** finding to production in days

---

## 0. Inputs and platforms

### Discovery sources

Findings originate anywhere. The flow must not care which.

| Source | Produces | Characteristics |
|---|---|---|
| AI discovery (Mythos-class) | Zero-days in first-party code | No CVE, no EPSS, arrives with a reproducing PoC |
| Veracode SAST | Static findings in source | Deterministic, re-scannable |
| Veracode SCA | Dependency CVEs | Deterministic, EPSS/KEV available |
| Veracode DAST | Runtime findings | Requires a deployed instance |
| Wiz | Container images, cloud posture | Artifact and configuration level |
| Qualys | Hosts, middleware | Infrastructure level |
| HackerOne / pen test | External reports | Human-authored, variable format |

### Normalization

**All sources convert to SARIF at intake**, and the canonical ID is minted at that moment.
This is the single most important structural decision in the flow: downstream stages never
branch on which tool found the defect, so adding a ninth source later costs a converter, not
a pipeline redesign.

Veracode exports SARIF natively. AI-discovery output requires a converter — this is net-new
work and it sits on the critical path.

### Platform roles

Two platforms sit between raw findings and the pipeline. Their roles are distinct and
neither is a tracker on its own.

#### IBM Concert — the finding system of record

- **Ingests every source.** `POST /ingestion/api/v1/upload_files` with
  `data_type=static_code_scan` accepts SARIF. `repo_name` and `repo_url` are required, which
  is what binds a finding to inventory. Optional `scanner_name` distinguishes the source.
- **Correlates the estate** — application, component and ownership context in one place.
- **Holds parent and child IDs**, status and SLA clock.
- Deployable **air-gapped** (VM and Kubernetes/OpenShift, with on-premises watsonx.ai), so
  findings need never leave the perimeter.

> **Boundaries.** Its risk score is `CVSS × EPSS × environmental` — CVE-derived, so
> AI-discovered findings score as nothing and need a separate priority band driven by PoC
> reproduction.

**Two capabilities are assumed and must be proven before the design depends on Concert.**
Both are cheap to test and both are load-bearing:

| # | Question | If the answer is no |
|---|---|---|
| 1 | **De-duplication.** Upload the same SARIF twice, then again with line numbers shifted by unrelated refactoring. Does it collapse to one finding? | Identity stays in an index we own; Concert becomes a reporting surface |
| 2 | **Reverse SBOM lookup.** Given a component and version, can it return every artifact that ships it? | Stage 2 needs our own reverse index; Concert contributes inventory context only |

Concert ingests both ConcertDef and CycloneDX SBOMs, with `repo_url` required for source
packages, so it *holds* the data needed for question 2. Whether it *exposes* that query is
an inference, not something the documentation confirms.

#### AWS Continuum — reachability and revalidation

- **Ranks children by real reachability** — which of the affected components is genuinely
  exploitable in the deployed application. This filters the child set *before* agent spend.
- **Revalidates a specific finding** — re-tests one selected finding against the live
  application and returns *Active* or *Resolved*, with history linked to the original.
- **Caps its own spend** via a task-hour ceiling that stops gracefully and retains partial
  findings. Worth copying as a pattern regardless of whether the product is bought.

> **Boundaries.** It tests the *running application*, not source. It therefore cannot assess
> un-deployed code — which is why it informs prioritization and confirms a fix held, rather
> than judging a proposed change. Its verdict is agent judgement, so it corroborates closure
> and must never certify it. It is also in gated preview.

### How platforms relate to proof

Concert answers **who is affected**. Continuum answers **whether it is really exploitable**,
and helps confirm a fix held. Neither certifies closure.

**The proof test committed alongside the fix does that** — deterministically, in
milliseconds, for years after both platforms have been replaced.

### Where each appears in the flow

| Stage | Concert | Continuum |
|---|---|---|
| 1 Identify | SARIF intake, de-duplication | — |
| 2 Scope | Inventory correlation → child IDs | Reachability ranking of the child set |
| 3 Agent | — | — |
| 4–6 Fix, PR, component release | — | — |
| 7 App validation | — | Revalidation against the assembled app |
| 8 Promote and close | Closure recorded against parent | — |

**Why Continuum sits at stage 2 and not stage 3.** It tests a running application, and at
stage 3 there is only a repo, a commit and a branch — no deployed instance of that code. The
only thing it can assess is the *currently deployed* version, which answers "is this defect
reachable in production right now." That is a prioritization question, so it belongs before
agent spend rather than during it. Running it at stage 3 asks the right question at the
wrong moment.

**What the markers do not claim.** Concert at stage 8 is bookkeeping — closure written back
to the system of record, which any tracker does. It is listed for traceability, not as a
capability claim.

---

## 1. Identity model

Two levels. This is the backbone of the design — everything else depends on it.

### Canonical ID — the defect

Minted at ingest, before anything else happens. Computed as a deterministic content
fingerprint over:

```
hash( component or repo identity
    + commit-pinned symbol/function identity
    + vulnerability class
    + finding signature )
```

**Never over line numbers.** They move on the first unrelated commit, and de-duplication
collapses. A re-scan that rediscovers the same defect must map to the existing record, not
open a second one.

### Child ID — one per affected component

Emitted after blast radius is resolved. Each child links to the parent.

**The parent closes only when every child closes.** This is what converts closure from an
assertion into a proof.

### Children are of two kinds — do not treat them alike

| | Source fix | Uptake |
|---|---|---|
| Count | ×1 | ×N |
| Where | The repo owning the vulnerable code | Every consuming repo |
| Work | Real engineering | Version bump |
| Agent | Yes — writes fix and proof test | No |
| Review | Human, required | Auto-merge on green |

For a defect in a shared library, uptake children typically outnumber the source fix ten to
one. Routing them through the agent path wastes the largest automation opportunity in the
flow.

---

## 2. The flow

### Stage 1 — Identify and mint identity

- All sources normalize to **SARIF** at intake. Downstream stages never branch on tool.
- Canonical ID minted and looked up: known fingerprint updates the existing record, new
  fingerprint creates one.
- SLA clock starts at ingest, not at triage.

### Stage 2 — Resolve blast radius

- Query the **SBOM reverse index** and application inventory.
- Output per affected component: repository, branch, commit.
- Emit one child ID per affected component, linked to the parent.
- **Rank the child set by real reachability** in the deployed application, before any agent
  spend. On a large fan-out this is what stops the programme paying to fix components where
  the defect is not reachable.

> The query that matters is the reverse one. Most SBOM tooling answers "what is inside this
> artifact." Remediation needs "a defect exists in this component — who ships it?" For a
> defect in an internal shared library there is no public advisory and no scanner that knows
> about it; the reverse index is the only mechanism that will ever tell consuming teams they
> are affected.

**Boundary:** SBOM covers declared dependencies only. Findings in bespoke application code,
or code copy-pasted between repos, appear in no SBOM and need fingerprint-based code
similarity detection instead. Budget for both.

### Stage 3 — Agent: fix or assess

The agent produces **two artifacts**, not one:

1. **The fix** — a PR against a remediation branch cut from the deployed release tag (not
   from `main`), carrying the child ID in the commit trailer.
2. **The proof test** — a test asserting the violated invariant, written against the *class*
   of bad input rather than one literal case.

The proof test **must fail against the pre-fix commit**. A test written after the fix proves
nothing: you cannot tell whether it is green because the defect is gone or because it never
captured the defect.

Alternative outcome:

- **Cannot fix** — routed to risk acceptance with a **mandatory expiry date**. Owner of this
  decision must be named (see Open Decisions).

*Reachability filtering has already happened at stage 2, so children that reach this stage
are ones worth spending on.*

> **Determinism comes from the test, never from the agent.** A model asked twice may answer
> differently; a test answers identically every time. Concert, Continuum or any similar
> platform may corroborate closure but must never certify it.

### Stage 4 — Human review

Code owner approves the PR. Already enforced by protected branches on all repositories — no
new control to build. This is the technical review and is not repeated later.

### Stage 5 — PR pipeline (delta-scoped)

Every scan is scoped to the change. Scanning the whole application per patch is what makes
remediation pipelines too slow to use.

| Gate | Scope | Budget | Mode |
|---|---|---|---|
| Secret detection | Diff | 10s | Block |
| Build | Component | 2m | Block |
| Proof test — pre-fix commit | The finding | 30s | **Must fail** |
| Proof test — fix commit | The finding | 30s | **Must pass** |
| SAST delta | Changed files only | 90s | Block on new |
| SCA | Changed dependencies | 40s | Block on new |
| Static quality | Branch analysis on diff | 60s | Block on new |
| Impacted tests | Selected by impact analysis | 2m | Block |
| Diff scope | Size and file spread | 1s | Warn / hard ceiling |

**Both proof-test runs are required.** Skipping the pre-fix run would certify a fix that
fixed nothing.

Deltas compare against the **branch point**, never an absolute policy threshold — otherwise
inherited debt blocks an unrelated fix.

### Stage 6 — Component release

- **Build once.** Sign the artifact and record the digest. Every later environment promotes
  this exact artifact.
- **Ephemeral environment by default**, spun up on demand and torn down after. Shared
  environments by documented exception only, recorded as a coverage gap.
- Child ID closes on successful deploy.
- **Sibling independence:** one child failing does not hold the others. The parent stays
  open.

> Rebuilding after testing ships something no gate examined. Promotion is a permissions and
> metadata operation — it must never be a compilation.

### Stage 7 — Application-level validation

Once every child component is released into the region, exercise the assembled application.
Components verified in isolation can still fail in combination.

- **Regression** — profile chosen by application tier and change class
- **Performance** — compared against the baseline of the release being patched
- **DAST** — against the assembled application, where runtime reachability is observable

Test selection is **automatic**. QA defines the profiles once per application and reviews
exceptions.

> **Coverage floors, not total coverage.** Each application tier carries a defined minimum;
> progressive delivery carries the residual risk. A programme that waits for complete
> regression coverage never starts.

### Stage 8 — Promote, deploy, close

- **Evidence pack assembled automatically** — every gate result, both proof-test runs, scan
  deltas, artifact digests, rollback rehearsal. Each item pre-evaluated to pass / warn / fail.
- **Compliance sign-off** on the pack, not on code. Target: under five minutes for a fully
  green pack.
- **Progressive deployment** — canary, then staged, with automated reversion on SLO breach.
- **Parent canonical ID closes** once every child reaches production. Attestation retained.

---

## 3. Human decision points

Exactly three. Each is a judgement automation cannot make.

| # | Decision | Question answered | Frequency |
|---|---|---|---|
| 1 | Code owner approves PR | Is this the right change to this code? | Per fix |
| 2 | QA owns test profiles | What must be proven before this app ships? | **Per application, once** |
| 3 | Compliance signs off | Is the evidence sufficient to release? | Per release |

**Deliberately absent:** no CAB per release, no central security review of every fix, no
separate QA sign-off per finding. Each would reintroduce a queue that scales with finding
volume — precisely the thing that must not scale.

---

## 4. Design rules that must not be violated

1. **Build once, promote thereafter.** No rebuild after testing, ever.
2. **Determinism comes from tests, not agents.**
3. **Deltas compare to the branch point, never to an absolute threshold.**
4. **The proof test must fail before it passes.**
5. **The parent closes only when every child closes.**
6. **Fingerprint on content, never on line numbers.**
7. **Branch from the deployed release tag, not from `main`** — otherwise the patch drags
   unreleased work with it and inherits the feature train's approval weight.

---

## 5. Capability requirements

Ordered by lead time, not effort.

| Capability | Why required | Status |
|---|---|---|
| SARIF normalization layer | Converts every source to one intake format; AI-discovery converter is net-new | Gap |
| SBOM store + reverse index | Resolves blast radius; only way to find consumers of an internal component | Partial — verify per-version retention |
| Finding platform (Concert) | Ingests all sources, correlates estate, holds parent/child IDs | **Prove dedupe + reverse lookup first** |
| Exploitability (Continuum) | Reachability ranking before agent spend; revalidation after | Gated preview |
| Delta code analysis | Every scan scoped to the change; current SAST platform lacks it | Gap |
| Branch-capable static quality | Per-branch and per-PR analysis — **verify edition licensing** | Verify |
| Elastic CI | Absorbs campaign bursts; static agent pools cap the programme | Gap |
| On-demand environments | Removes environment booking from the critical path | Gap — per app |
| Test impact selection | Keeps pipelines inside budget as volume rises | Gap |
| Proof-test harnesses | A small set per runtime, built once, reused across the estate | Gap |
| AI remediation agent | Generates the fix and the proof test | Evaluating |

---

## 6. Sequencing

**Phase 0 — Prove the platform assumptions.** Two tests, days not weeks, before any
architecture depends on them: Concert SARIF de-duplication, and Concert reverse SBOM lookup.
Both outcomes are acceptable; not knowing is not.

**Phase 1 — Prove the spine.** Canonical and child IDs, SBOM reverse index, one pilot
application end to end. Success is a *provable* closure, not a fast one.

**Phase 2 — Make it fast.** Delta scanning, elastic CI, impact selection, ephemeral
environments. Pipeline time budget enforced.

**Phase 3 — Make it wide.** Onboard by tier. Uptake children auto-merged. Agent introduced
on the source-fix path.

**Continuous — Prevent.** Automated dependency currency, so the majority of future findings
never reach this pipeline at all. This removes more findings than any pipeline improvement
and should run alongside all three phases.

---

## 7. Metrics

**Finding to production** — elapsed time from ingest to the last child ID running in
production, p50 and p95. Measured on the *parent*, so partial remediation cannot be reported
as success. Tickets closed, scan pass rates and SLA compliance can all improve while this
number gets worse.

**Pass rate per gate** — any gate that has not failed in a quarter is not protecting
anything. Remove it and return the time to the pipeline.

---

## 8. Open decisions

- **Who owns risk acceptance** when the agent cannot fix a finding, and what expiry applies.
- **Embargo handling** for findings with no public advisory — restricted tier for the work
  item, and separation of any exploit artifact from the ticket.
- **Cost tier for on-demand environments**, which otherwise becomes the programme's largest
  line item at this scale.
- **Static quality tool edition** — confirm branch/PR analysis is licensed before design
  depends on it.
