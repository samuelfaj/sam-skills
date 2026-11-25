# Capturing product screens

Use when the PDF shows a running product. The goal is many sharp screens of one realistic journey, captured by a script you can rerun.

## Environment

- Run the real product locally against a disposable database or container you start for this. Never capture from production data or another person's account.
- Reuse the project's browser-test harness (fixtures, seeded roles, fake payment and calendar providers, blocked third-party requests) instead of building new infrastructure.
- Write the capture as one temporary browser test, kept outside the product's committed tests. Delete it after the PDF is done, or ask before committing it.
- Stop every container and server you started, and delete scratch output that holds personal-looking data.

## Data

- Follow one fictional persona through the whole flow, plus the few extra records staff screens need to look populated (two or three more people, one lead).
- Use realistic names, e-mails on an example domain, valid-format test documents and the provider's test card. Never a real person's data.
- Fill every field with plausible content. Empty states only where the empty state is the point.
- When a step needs time to pass (a 14-day check-in, a consultation in the past), move dates in the disposable database, and only there.
- Uploads (body photos, documents) use neutral generated placeholders clearly marked as examples.
- E-mails captured from the local outbox: replace local addresses with the public domain before rendering them.

## Capture settings

- Desktop 1440x900 and phone 390x844, `deviceScaleFactor: 2`, phone contexts with touch enabled.
- Before each shot wait for the network to go idle, `document.fonts.ready` and spinners to disappear. Wait for the specific response of an action (`waitForResponse`) instead of sleeping.
- Prefer a viewport shot. For a longer page, grow the viewport height up to a cap (about 2400 px) and shoot, then restore it; this keeps sticky sidebars and headers in place, unlike full-page capture.
- Use element shots for a single panel (a table, a dialog, an e-mail).
- Capture the state that explains the step: the form filled before submit, the confirmation after, the other role's view of the same record.
- Save a manifest (file, URL path, viewport) next to the images; layout decisions such as sidebar crops depend on it.

## Review before layout

Build contact sheets of every shot and look at all of them. Recapture any shot with a spinner, an error, an overlay covering content, an empty list that should have data, a technical id where a name belongs, or a test URL. Note real product defects you see; they belong on the open-items page, not hidden by cropping.
