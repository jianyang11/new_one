# Private machine-tool v3 — S-C API amendment 3

**Frozen:** 2026-07-14, after the recorded 98/100 S-C capacity result and
before any additional S-C request.

## Authorization and purpose

The user explicitly authorized up to 100 further S-C API requests. The prior
run had already admitted all 20 normal-machining and all 20 lead-screw samples,
while base imbalance had 18/20 after its two remaining original slots exhausted
their fixed initial-plus-three-feedback limits. This amendment is a bounded
pool-capacity iteration; no S-C downstream metric exists and no formal file has
been read. It is not an outcome-based change to a renderer, prompt direction,
admission gate, or downstream protocol.

## Fixed extension

The cumulative S-C ceiling becomes 200 counted requests. Only two new
`base_imbalance` replacement slots, numbered 20 and 21, are eligible. Each has
the unchanged initial response plus at most three structured-feedback responses,
the unchanged prompt, exact recipe schema, deterministic renderer, three
expansions per recipe, class-identity certificate, verifier, duplicate check,
and diversity rule. Thus the extension can consume at most eight further
requests; authorization that is not needed is not consumed.

The target remains exactly 20 admitted samples per class. No normal or
lead-screw slot is added, no previously exhausted slot is reopened, and a
rejected waveform is never modified or repaired. Construction stops when the
two replacement slots are resolved or exhausted. S-C downstream remains
forbidden unless the final count is exactly 20 in every class; formal IDs 7/8
remain prohibited regardless of this capacity extension.

## Audit trail

The earlier 98-request outcome remains frozen in
`mt_private_v3_s_c_capacity_failure.md`. The API ledger continues from request
99, storing only hashes, transport status, and gate outcomes—not credentials or
response contents. The final extension decision will report the total count and
whether a balanced pool was formed.
