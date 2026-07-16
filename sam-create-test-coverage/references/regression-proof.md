# Regression Proof

A useful regression test must distinguish the defective contract from the intended one.

## Proof methods

- `RED_GREEN`: run the targeted test against a safely available defective state,
  then against the corrected state.
- `MUTATION`: make one focused reversible change in an isolated copy and show the
  test fails for the expected reason.
- `CONTRACT`: cite an authoritative local schema, invariant, route, type, or
  requirement and assert that exact boundary.
- `NOT_PROVEN`: explain why discrimination could not be tested safely.

Do not reset or modify the user's checkout to recreate the defect. Do not use a
mutation that changes unrelated behavior. Record the exact command and observed
failure for red/green or mutation proof.

Reject tests that pass both defective and corrected behavior, assert only fixture
literals, or prove mock calls while the user-visible contract remains untested.
