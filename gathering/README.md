# Gathering 02

This round checked the four line tools against their saved real observations and through one read-only live request each, added [Change Context](../shared/change-context/README.md) for code and call comparisons, refreshed the no-coin decision, rebuilt the gallery, and painted a small paired-stone motif beside the earlier Pepe.

- [REPORT.md](REPORT.md): per-line commands, outcomes, limits, overlap and 21-step boundaries.
- [COINS.md](COINS.md): none; no launch or deploy order.
- [VISUAL.md](VISUAL.md): wall and thumbnail dimensions, preservation, visual review and limits.
- [Gallery](../dist/index.html): every numbered record by wall, newest painted rounds first.

Rebuild the self-contained gallery and exact four-goal JSON from current records:

```sh
python3 -B gathering/build_gallery.py
```

Gathering 01 already initialized future placeholders. Normal rebuilding does not modify them. `--initialize` is only for a cave before its first gathering and now refuses to run.
