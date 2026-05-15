---
name: sam-create-task-demo-video
description: Create human-readable task demo videos with Playwright, always convert to MP4, validate playback, upload to GitHub or GitLab, and comment on the PR or MR by default.
---

# Sam Create Task Demo Video

Use this skill when the user asks for a human presentation video of a task, feature, regression, or bug fix working from beginning to end.

This skill is for a demo video, not a fast automated test recording. Use Playwright as the camera and browser controller, but optimize the result for human review.

## Operating Role

You are a senior QA automation engineer and product-minded software engineer.

Create a clear visual walkthrough that demonstrates the task or bug fix in the same surface a human reviewer would use. The final artifact must be an `.mp4` video unless the user explicitly cancels the video request.

## Defaults

- Produce a guided visual demo without required narration.
- Show the full flow from initial state to final verified result.
- Start the application before recording.
- Use the real running UI unless it is impossible after serious startup/linking
  effort. Mocked pages, component previews, or request-only proof are fallback
  evidence only.
- Do whatever local setup is necessary to open both UI and backend for the demo:
  direct process start, Docker, compose, repo scripts, dependency services,
  seeded data, local env overrides, and port changes are all allowed when they
  are local/dev-safe.
- If the default ports conflict or the UI points at the wrong API, change local
  ports, env vars, compose overrides, or Playwright config so the browser uses
  the running backend. Report those changes.
- If the user explicitly says the environment is dev and the database is a dev
  database, prefer real dev data when it makes the demo more truthful and does
  not expose secrets or private user data.
- If frontend and backend are separate repositories or services instead of one
  monorepo, bring both up directly or through Docker/container workflows, link
  the frontend to the backend, and record against that linked local/dev stack.
- Use a stable viewport and readable pacing.
- Add temporary captions or browser overlays when they make the demo easier to understand.
- Keep the demo focused on the requested task or bug; do not turn it into a broad product tour.
- Always convert Playwright output to `.mp4`, even when the raw recording is `.webm`.
- Verify the `.mp4` opens and shows the intended flow.
- Upload the `.mp4` and comment on the GitHub PR or GitLab MR by default when a PR or MR can be resolved.
- Do not commit video files to the repository unless the user explicitly asks for versioned artifacts.

## Step 1: Understand The Demo Target

Identify the user-visible behavior that must be demonstrated:

- The task or bug being shown.
- The initial state that makes the change understandable.
- The exact user actions to perform.
- The final result that proves the feature works or the bug is fixed.
- Any relevant acceptance criteria, PR/MR comments, issue text, or QA notes.

If the task involves a bug fix, prefer a before/after structure only when a before state is available without unsafe rollback or extra implementation work. Otherwise, show the corrected behavior and clearly state that the demo proves the fixed state only.

## Step 2: Discover Environment And PR/MR

Inspect the repository and current branch to determine:

- How to run the app locally.
- Whether the app is a single monorepo or needs separate frontend/backend services.
- How to start required services directly, through Docker, or through the
  repo-supported container workflow.
- How the frontend should be configured to call the local/dev backend.
- Which local ports/env/config can be changed if defaults conflict or do not
  link UI to backend.
- Which URL, route, or screen starts the flow.
- Which seed data, account, feature flag, or test fixture is safe to use.
- Whether the user explicitly confirmed dev environment and dev database access,
  allowing safe use of real dev data.
- Whether the repo uses GitHub or GitLab.
- The current PR or MR, from an explicit URL, the current branch, or platform CLI lookup.

Use `gh` for GitHub repositories and `glab` for GitLab repositories. If the user provided a full PR/MR URL, resolve the platform and target repo from that URL instead of assuming the current checkout.

If Docker, direct startup, port/config changes, linked-service startup, or real
dev data access is blocked, record every attempted path and the exact blocker
before using the closest safe runnable local/dev environment.

## Step 3: Write A Human Demo Script

Before recording, create a short script for the video:

- Title: one sentence naming the task or fix.
- Opening: what screen or state the reviewer is seeing.
- Action sequence: the exact user actions in order.
- Proof moment: the specific visible result that confirms success.
- Ending: final stable state to pause on before stopping.

Keep the script concrete and reviewer-oriented. Avoid implementation-only language in the video unless the task itself is developer-facing.

## Step 4: Record With Playwright

Start the app, link UI and backend when the flow crosses that boundary, and
record the flow locally with Playwright or the project's equivalent browser
automation setup.

If the flow crosses frontend/backend boundaries and those services are not in a
single monorepo, start or verify both directly or through Docker/container
workflows, configure the frontend to call the local/dev backend, adjust local
ports/config as needed, and record only after the linked stack is reachable from
the browser.

Recording requirements:

- Use a stable desktop viewport unless the task is mobile-specific.
- Prefer user-facing locators and existing app routes.
- Use deterministic data and reset state when needed.
- Prefer real dev data only when the user has explicitly confirmed dev database
  usage; otherwise use safe seed data, fixtures, or test accounts.
- Slow the flow enough for human review by adding short waits at meaningful points.
- Pause briefly on the initial state, before the key action, and on the final proof state.
- Avoid flaky waits; wait for visible UI state, network completion, or app-specific readiness signals.
- Hide or avoid secrets, tokens, private user data, credentials, and sensitive production information.
- Keep every safe relevant recording that demonstrates the task clearly. Do not
  drop a relevant video just to keep the PR/MR comment shorter.

Temporary captions or overlays are allowed if they are injected only in the browser session and do not modify repository files. Captions should label steps, not explain internal implementation.

## Step 5: Convert To MP4

The final video artifact must be `.mp4`.

If Playwright creates `.webm`, convert it to `.mp4` with the locally available video toolchain, such as `ffmpeg`, using a broadly compatible codec. Do not treat `.webm` as the deliverable.

Name the final file clearly, for example:

- `.artifacts/demo-videos/<task-or-branch>-demo.mp4`
- `playwright-report/<task-or-branch>-demo.mp4`

If conversion fails, report the exact blocker and keep the raw recording only as diagnostic evidence. Do not upload the raw file as the final demo unless the user explicitly approves the fallback.

## Step 6: Verify Playback And Safety

Before uploading or reporting completion:

- Open or inspect the `.mp4` to confirm it plays.
- Verify the recording used the real running UI and, when applicable, the linked
  frontend/backend local/dev stack. If fallback proof was used, document why the
  real UI could not be opened despite direct, Docker, port/config, and linking
  attempts.
- Confirm the video shows the intended beginning, action sequence, proof moment, and ending.
- Confirm captions or overlays are readable if used.
- Confirm no secrets, credentials, tokens, private user data, or sensitive production information are visible.
- Confirm the video is not an ultra-fast test artifact.

Do not claim a successful demo video until the `.mp4` playback has been verified.

## Step 7: Upload And Comment By Default

When a PR or MR can be resolved, upload every safe relevant `.mp4` and add a
comment by default. This is mandatory for all task demo videos unless upload is
blocked by platform or auth limitations.

GitHub:

- Use `gh` to find the PR for the current branch when no PR URL is provided.
- Upload every safe relevant `.mp4` using the best available GitHub attachment path.
- If direct upload is not supported by the available `gh` setup, use an available `gh` extension or helper that creates GitHub user attachments.
- Comment on the PR with each uploaded video in the exact GitHub-renderable
  format: a raw `https://github.com/user-attachments/assets/<id>` URL alone on
  its own paragraph with a blank line before and after it. Do not wrap GitHub
  user-attachment video URLs in Markdown link or image syntax.
- Re-read the posted PR comment with `gh` or `gh api` and confirm every uploaded
  video is present in that raw URL format, not a local path or committed artifact
  path.

GitLab:

- Use `glab` to find the MR for the current branch when no MR URL is provided.
- Upload every safe relevant `.mp4` with the GitLab Markdown Uploads API through
  `glab api`.
- Comment on the MR with the exact `markdown` field returned by the GitLab upload
  response for each video. Do not manually build GitLab upload URLs from `url`,
  `full_path`, project ids, repository paths, `/raw/...`, or committed artifact
  paths.
- Re-read the posted MR note with `glab api` and confirm every video appears as
  `.mp4` Markdown using `/uploads/...`, exactly from the upload response.

If upload or commenting is blocked for any safe relevant video, do not fail
silently. Report the exact blocker, the local `.mp4` path, the attempted command,
and any command or auth issue that prevented upload.

Never commit video files to the repository unless the user explicitly asks for versioned video artifacts.

## PR/MR Comment Template

Use a concise comment like this:

```markdown
## Task demo video

Recorded a human-paced demo of the requested task/fix.

- Scenario: <what the video demonstrates>
- Environment: <local/dev/staging and URL if safe>
- Validation: playback verified; final state shows <proof moment>
- Video: <GitHub raw user-attachments URL, or GitLab exact upload markdown>

Limitations: <none, or exact limitation>
```

Keep the wording honest. Do not say the task has full automated coverage unless automated tests were also implemented and passed.

## Completion Report

At the end, report only the useful evidence:

- Local `.mp4` path.
- PR/MR comment link when available.
- Upload status.
- Posted format verification status for each uploaded video.
- Playback verification status.
- Any limitation or blocker.

If the user requested the strongest possible proof, include the app environment and exact flow covered, but keep the summary short.
