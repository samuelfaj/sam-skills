# Release Mode

Apply freeze discipline to release, beta, stable, hotfix, signing, packaging,
publishing, notarization, deployment, or release-check work.

- Freeze the exact target branch or ref before review.
- Accept only release blockers, failed release infrastructure, exact backports,
  install or upgrade breakage, data loss, crashes, and concrete security exposure
  as reasons to expand the release patch.
- Move non-blocking design and maintainability concerns to `FOLLOW_UP` for the
  normal development branch.
- Do not introduce new product behavior, public contracts, configuration surfaces,
  migrations, ownership boundaries, or process policy unless required to unblock release.
- Tie every accepted release finding to the shipped-risk path and smallest proof.
- Record whether an emergency fix must also be forward-ported.
- Stop and escalate when the safe correction requires a larger redesign or rollout decision.
