# Method

Advice does not change behavior. A file the checker can fail does.

## Completeness versus size

Gates decide whether the asked outcomes exist. The ladder decides how little
code those outcomes may take. A small diff that misses a gate is unfinished.
A complete custom stack where the standard library already holds is waste.
Run the ladder after you understand the change, then keep running gates
until the file, not your mood, says done.

## Before any deliverable

1. Read the request and the live flow it touches. Bug fix: grep every caller
   and fix the shared function once.
2. Count independent units. Independence means neither needs the other's
   in-progress state.
3. State the split-gate decision from the skill contract. Below the
   floor, stay solo and say so. Force-splitting a one-row task is the
   same error as refusing a twelve-unit split.
4. Write `GATES.md`. If the gate is open, write `DELEGATION.md` immediately
   after, still before deliverable files. Tree 4+ also writes `PLAN.md`
   and one gates file per leaf and branch.

## Depth

Depth is decomposition, not an effort multiplier. Leaves are real work:
about ten minutes, one deliverable, one gates file. Smaller means you went
too deep. Hidden extra deliverables means you did not go deep enough.

- Tree 2–3: feature, bug hunt, document. Solo.
- Tree 4–5: subsystem or serious refactor. Delegated.
- Tree 6–7: whole project to a high bar. Delegated, disjoint leaves,
  integration gates at every merge.

If the user gives no N, pick the smallest depth whose leaves match the
joints. Do not add a layer by default.

## Work

Solo: four passes on the minimal solution against one gates file.

Delegated: coordinator plans, dispatches, verifies, and integrates.
Workers receive a brief, not the parent transcript. Fresh context per
unit is the point; attention is the scarce resource.

Each leaf is finished when its gates are met with evidence **and** a full
improvement pass finds nothing, whichever is later.

## Finish line

No `COMPLETE` while any gate is unmet, any delegated row is not
`verified`, any reported number is unremeasured, or a new package landed
that the user did not name. `ABANDON: <id> <reason>` is the honest exit
for an impossible gate. Silent scope-narrowing is not.
