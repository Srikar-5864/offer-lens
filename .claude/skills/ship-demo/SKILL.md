---
name: ship-demo
description: Final 30-minute ship routine for OfferLens — green checks, real numbers into README and deck, Known gaps, backup recording, rehearsal. Use when the user says ship, wrap up, final, or demo prep.
---

# Ship the demo

1. `make check` green. Fix, don't skip.
2. `make eval report` from a clean state; confirm README table and `reports/chart.svg` updated.
3. Write **Known gaps** in README + EVAL.md (Lexsi kit workarounds, test set sizes, synthetic→real gap, top error buckets).
4. Collect deck numbers into `reports/deck_numbers.md`: schema-valid / field_acc / hallucination for A,B,C (synthetic + real),
   CuratorKIT generated vs kept + top 3 rejection reasons, train time, p50 latency, rps, cost per 1k (with cited source).
   Every number must trace to a file in `reports/` or `data/curated/manifest.json`.
5. Record a 60–90s screen capture of DEMO_SCRIPT steps as `reports/demo_backup.mp4`.
6. Pre-load demo inputs: the 8 examples + the Hinglish forward + the injection example in a text file.
7. Rehearse DEMO_SCRIPT.md twice with a timer. Kill all non-demo processes on the GPU box.
