# Private machine-tool v3 — S-C smoke report

- Decision: `PASS`; one admitted candidate per class.
- API ledger: `7/100` total attempts; formal IDs `7/8` read: `0`.
- Requests 1--3 received HTTP 200 but were parser-only failures under the
  original whole-message JSON decoder. Amendment 1 preserved their counted
  status and decoded wrapped JSON without relaxing the recipe schema.
- Requests 4--5 admitted base imbalance and lead-screw anomaly. Request 6
  produced a normal candidate rejected only by the unchanged Y `psd_w1` gate.
  Amendment 2 used one of that slot's remaining structured-feedback rounds;
  request 7 admitted normal machining with every verifier, identity,
  duplicate, and diversity check passing.

The accepted normal candidate's Y PSD-W1 is `0.02202`, below its unchanged
threshold `0.08519`. No waveform was repaired and no gate was changed.
Full S-C pool generation is now eligible under the frozen 100-request total
ceiling.
