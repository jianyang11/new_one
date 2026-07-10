# MFPT Availability Audit

Date: 2026-07-05

## Source Checked

- Requested historical/public entry: `https://www.mfpt.org/fault-data-sets/`
- Saved HTML: `data/mfpt/meta/fault-data-sets.html`
- HTTP check on 2026-07-05:
  - `https://www.mfpt.org/fault-data-sets/` returns `301`
  - Redirect target: `https://www.asnt.org/about/managed-affiliates/mfpt/`
  - Final page returns `200`
  - Canonical page title: `MFPT Society | Advancing Mechanical Reliability & Failure Prevention`

## Download-Link Audit

The saved page is an ASNT/MFPT society information page, not a dataset index.
Constrained extraction found no direct public dataset links with `.mat`, `.zip`,
`.csv`, `.rar`, `.7z`, `.tar`, or `.gz` targets. The only data-related links
matching the audit terms were contact mail links:

- `mailto:datamanagement.ai@mfpt.org`

The page text mentions data management activity and "download to ground
stations" as part of a general mission description, but this is not a dataset
download endpoint and cannot support a reproducible experiment.

## Decision

MFPT is blocked for the current reproducible public-dataset pipeline unless a
verifiable public download URL, archive, or license-cleared mirror is supplied.
It must not be counted as an included public dataset, and no MFPT performance
claim should be added to the manuscript.

## Next Action

Continue with other public sources whose official download endpoints can be
verified and logged. If the user provides a current MFPT archive URL, repeat the
same protocol used for CWRU: smoke download, schema audit, checksum/size log,
preprocessing, split freezing, and downstream smoke before any full run.
