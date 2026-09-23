# Method

## Depth

Depth is decomposition, not an effort multiplier. A leaf is real work: about ten minutes, one deliverable, one gates file. Smaller means you went too deep; hidden extra deliverables mean you did not go deep enough.

| Tree | Scope | Mode |
| --- | --- | --- |
| 2–3 | Feature, bug hunt, document | Solo |
| 4–5 | Subsystem or serious refactor | Delegated |
| 6–7 | Whole project to a high bar | Delegated, disjoint leaves, integration gates at every merge |

No N given: pick the smallest depth whose leaves match the joints. Never add a layer by default.

## Leaf finish

A leaf is finished when its gates are met with evidence **and** its review pass (SKILL.md step 5) ends, whichever is later. Defects found outside that leaf's gates are parked; they do not reopen the leaf.
