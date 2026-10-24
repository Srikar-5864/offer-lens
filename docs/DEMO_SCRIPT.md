# Demo script — 4 minutes

**0:00 Hook (20s)** — Hold up phone with a real WhatsApp deal forward. "Every Indian deals app has to read
thousands of these a day. Today that means paying a closed model per message. We did it on a 1.5B model, locally."

**0:20 Live demo (90s)** — Extract view.
1. Click the `bank_tnc` example → Extract. Point at receipt + colored source underlines. "Every value traces back to the text."
2. Paste the Hinglish forward live (keep it in clipboard). Extract. "Code-mixed, emojis, relative date — resolved."
3. Paste the injection example ("ignore previous instructions…"). "Grammar-constrained: it can only ever emit this schema."

**1:50 The insight (60s)** — Compare view, then Results.
"Grammar alone gets you valid JSON — look, valid, but the cap and the date are wrong. Fine-tuning fixes the values."
Read the three numbers off the Results page: schema-valid, field accuracy, hallucination rate for B vs C.

**2:50 Pipeline (40s)** — one slide: CuratorKIT (N generated → M kept, top rejection reasons) → AlignTune (LoRA, X min) → AuditKIT + SGLang.
Say the real-test result separately from synthetic. Mention one honest failure bucket.

**3:30 Close (30s)** — cost per 1k vs closed API (cited), "this goes into DealFeed next week", thank the sponsors.

Backup: if the GPU box dies, play `reports/demo_backup.mp4` and keep talking over it. Never debug on stage.

Likely judge questions — have answers:
- Why not just prompt a bigger model? → cost/latency/privacy numbers.
- Is your test set leaked? → real set hand-labelled, never trained on; synthetic test generated with held-out seeds.
- What does CuratorKIT actually buy you? → rejection breakdown from manifest.json (+ ablation if done).
