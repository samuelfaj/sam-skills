---
name: sam-humanizer-short
description: Rewrite chat messages (Slack, DMs, PR comments, bot replies) so they sound like a real person typing fast. Short lines, line breaks, no essay paragraphs. Use when text reads like an AI or a long report.
---

# Sam Humanizer Short

Rewrite the text the way a coworker types in Slack.

## Non-Negotiable Contract

Keep every fact, name, number and path exact. Change only the shape and tone.

## Shape

- One idea per line.
- Blank line between ideas.
- 1 to 3 short lines per message. Split longer content into separate messages or lines.
- Lead with the answer or the ask. No warm-up.
- No headers, bold, bullet lists or tables in chat.
- Fragments are fine: "Ok", "Oh, I didn't go through, just saw the post".

## Voice

- Plain words. Contractions. Say "I" and "you".
- Say what you saw, what you did, what you need. Stop there.
- Casual links and emoji are fine, rarely. One at most.
- Small imperfections are fine (lowercase start, no final period).

## Cut

- Openers: "Great question", "Certainly", "I hope this helps".
- Closers: "Let me know if...", "Feel free to...".
- Recaps, hedging, "It's worth noting", "Additionally", "Moreover".
- Lists of three for rhythm, inflated words, em dashes.
- Explaining what you are about to say.

## Return

Return only the rewritten message, ready to paste. No commentary.

## Example

Before:
"The gaps: nothing makes the reviewer name the failure that matters, and section 3 accepts any green test job even if it never selected the suite in question."

After:
Hey, found two gaps.

Reviewer never has to name the failure that matters (timeout, failed retry).

And a green CI job counts even if it never ran that suite. That's how the e2e one got a free pass.

I'd add one check to 0.1 for this.

## Keep exact

Code, commands, paths, names, numbers and error strings stay untouched. Reply in the user's language.
