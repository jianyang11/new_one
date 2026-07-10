# Phase-B CWRU LLM Smoke Combined Gate Report

Date: 2026-07-06

## Scope

- Phase-B order: CWRU first, before XJTU and IMS.
- Protocol: CWRU 12 kHz drive-end, `within_load0`, train-only verifier calibration.
- API discipline: serial requests, interval >=2.2 s, max_tokens<=900, retries<=3.
- CWRU small-batch API cap used here: 30 requests total.
- API key is not stored in project files.

## Runs

| tag | classes | planned slots | API requests | cumulative API | decision |
|---|---|---:|---:|---:|---|
| `smoke_api_v1` | healthy/IR/B/OR | 20 | 20 | 20 | `FAIL_NEEDS_ITERATION` |
| `smoke_api_v2_healthy_prompt` | healthy | 10 | 10 | 30 | `FAIL_NEEDS_ITERATION` |
| `smoke_api_v3_healthy_compact` | healthy | 10 | 10 | 40 | `PASS_FOR_DOWNSTREAM_SMOKE` |

API usage log: `breeze/results/phaseB_api_usage_log.csv`.

## Acceptance

| run | class | slots | accepted slots | accepted items | slot acceptance |
|---|---|---:|---:|---:|---:|
| `smoke_api_v1` | healthy | 5 | 0 | 0 | 0.000 |
| `smoke_api_v1` | IR | 5 | 5 | 23 | 1.000 |
| `smoke_api_v1` | B | 5 | 5 | 23 | 1.000 |
| `smoke_api_v1` | OR | 5 | 5 | 25 | 1.000 |
| `smoke_api_v2_healthy_prompt` | healthy | 10 | 0 | 0 | 0.000 |
| `smoke_api_v3_healthy_compact` | healthy | 10 | 10 | 42 | 1.000 |

## Failure Analysis

`smoke_api_v1` showed that LLM recipes for IR/B/OR are compatible with the CWRU renderer and train-calibrated verifier. The blocker is healthy generation. The five healthy recipes parsed and followed the high-level schema, but all failed admission, mainly because the broad band-weight background did not reproduce the train-supported healthy PSD shape:

- Healthy v1: 0/5 accepted slots.
- Dominant failures: PSD W1 above the healthy threshold and soft spectral fraction violations.
- Example PSD W1 values: roughly 138-172, threshold 57.524.

`smoke_api_v2_healthy_prompt` added full-band healthy component anchors derived from the training PSD. The model did move in the intended direction and started emitting many narrowband components, but all 10 responses were truncated or incomplete under the max_tokens<=900 constraint:

- Healthy v2: 10/10 parse failed.
- Root cause: asking for 20-30 components makes the JSON too long for the 900-token cap.

Local non-API renderer tests show that healthy acceptance is possible without PSD-template injection when the recipe uses a compact set of dominant full-band components. In those tests, 5-10 components plus low broadband noise passed the same verifier for multiple seeds. This is a prompt/recipe-compactness problem, not evidence that the CWRU healthy verifier is impossible to satisfy.

`smoke_api_v3_healthy_compact` reduced the healthy prompt to exactly 8 dominant component anchors and compact JSON. This repaired admission without PSD-template injection:

- Healthy v3: 10/10 accepted slots.
- Accepted healthy items: 42.
- Combined smoke pool: `breeze/runs/phaseB_cwru_within_load0_llm_smoke_combined_v3/pool.npz`.
- Combined by-class counts: healthy 42, IR 23, B 23, OR 25.

## Gate Decision

Admission decision: `PASS_FOR_DOWNSTREAM_SMOKE`.

Reason: after the approved 10-call v3 repair, every CWRU class has accepted LLM slots under the train-only verifier. However, downstream smoke is still not strong enough to justify full-pool scale-up. See `breeze/results/phaseB_cwru_llm_smoke_v3_report.md`.

## Next Iteration Proposal

The next defensible iteration is a compact healthy-only prompt, using exactly 5-8 dominant component anchors and compact JSON output. The script now supports this via `--healthy-anchor-count` and defaults to 8. The next run should be a new tag, for example:

`smoke_api_v3_healthy_compact`

Status after approval: v3 used 10 additional API requests, cumulative Phase-B API usage is now 40. Do not run 150/class CWRU LLM generation until downstream smoke instability is diagnosed and repaired.
