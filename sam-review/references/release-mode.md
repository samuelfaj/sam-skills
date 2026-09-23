# Release Mode

- Freeze the exact target branch or ref before review.
- Expand the release patch only for release blockers, failed release infrastructure, exact backports, install or upgrade breakage, data loss, crashes, or concrete security exposure.
- Move non-blocking design and maintainability concerns to `FOLLOW_UP` for the normal development branch.
- Add no new product behavior, public contracts, configuration surfaces, migrations, ownership boundaries, or process policy unless required to unblock the release.
- Tie every accepted release finding to the shipped-risk path and its smallest proof; record whether an emergency fix must also be forward-ported.
- Stop and escalate when the safe correction requires a larger redesign or rollout decision.
