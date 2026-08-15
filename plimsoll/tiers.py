"""Task-shape floors, denominated in absolute tokens.

Every number here is ASSERTED, not promoted. They ship with the evidence that
supports them so they can be argued with:

- `originating` 50,000 — anchored on published long-context results (NoLiMa:
  11 of 13 models below half their baseline at 32K; Chroma: decline begins
  immediately rather than at a cliff).
- `executing` 150,000 — NO SOURCE. An interpolation between a defensible floor
  and no floor. This should be the first number the corpus contradicts.
- `mechanical` — ungated, from the finding that retrieval survives far longer
  than multi-step reasoning.

The percentage of the window is never consulted. That is the whole point: a
fraction gets monotonically more permissive as windows grow, so 40% of 200K and
40% of 1M are not the same claim.
"""

FLOORS = {
    "originating": 50_000,
    "executing": 150_000,
}

#: The lowest number in the table. Below this every shape is permitted, so the
#: model has no decision to make and is told nothing.
LOWEST_FLOOR = min(FLOORS.values())
