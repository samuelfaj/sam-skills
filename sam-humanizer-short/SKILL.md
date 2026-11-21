---
name: sam-humanizer-short
description: Rewrite a Slack message, WhatsApp reply, DM, PR comment, or bot update in a natural chat voice. Use when a draft sounds scripted, overly formal, or like a report.
---

# Sam Humanizer Short

Read the last turn if one is supplied. What would the recipient need to hear from this speaker right now? In a thread, answer the open question. In a new channel post, name the thing that happened so someone coming in cold can follow. If the draft already fits the conversation, leave it alone.

## Voice and rhythm

- Take your cue from how the **sender** talks to this audience. Someone who writes “pra” to a teammate may write “você poderia” to a client. In English, keep the sender’s own contractions and technical vocabulary. With little context, ordinary conversational wording is enough.
- Let the thought set the length. A confirmation may be two words. A decision may need a paragraph to explain what led to it, then a question on its own. Keep a qualification next to the claim it changes. Break where the speaker changes thought.
- Keep warmth that does something. A greeting can open a new conversation. Thanks can acknowledge someone’s effort. In an ongoing exchange, it’s fine to get straight to the answer. Keep expressive punctuation, humor or emoji when they belong to this sender and moment. Adding typos, slang or a pet nickname to manufacture personality usually sounds forced.
- Turn report headings into sentences someone could say. A short list is useful when the reader has several things to check. Drop the ceremonial intro, commentary on the team, repeated takeaway and sign-off when they add nothing. Preserve a real recommendation or request.

## Non-Negotiable Contract

Keep the facts and who saw, tested or promised what, including when the speaker is a bot. Copy names, identifiers, numeric values and their units, dates, links, code, commands, paths and error strings as supplied. A suspicion stays a suspicion. A proposed action stays proposed. Never invent an observation, recommendation, deadline, fix or offer to make the message flow.

## Return

Return just one pasteable message unless the user asks for separate sends. Follow the requested language. Otherwise keep the language of the message, even if the editing instructions are in another language.

For text someone will paste into Slack or WhatsApp, put a bare URL beside the ticket or file it opens. Skip Markdown link syntax or bold heading markers that the recipient might see as literal text. In a Markdown PR comment, a linked issue number is fine.

## Examples

**WhatsApp, answering a question.** Someone asks “Qual dos dois portões?” The draft says “A entrada é pelo portão menor.” Send “Pelo menor”. The earlier turn supplies the rest.

**Slack, explaining a choice.** The draft says “Após vermos as duas provas impressas, nossa preferência é pela versão creme. O texto na cinza ficou difícil de ler. Gostaríamos de saber se podemos seguir com a creme.”

> A gente gostou mais da creme quando viu as duas no papel. Na cinza ficou difícil de ler o texto.
>
> Podemos seguir com a creme?

**English, technical reply.** Asked whether the export is fixed, the draft says “The job ran again. Confirmation that the resulting file opens is still pending.” Send “The job ran again. Still waiting to hear if the file opens.”
