# Output Contract

Keys are exact (missing or extra keys fail); `schema_version` is `1`. Keep the scaffold's *derived* values.

| Field | Rule |
| --- | --- |
| `target` `{base_sha, head_sha, context_fingerprint}` | *derived* from the context |
| `language` | non-empty; `EN-US` unless another language was explicitly requested |
| `change_types` | non-empty, unique: `BUG_FIX`, `NEW_FEATURE`, `REFACTOR`, `DOCUMENTATION`, `OTHER` |
| `file_coverage[]` `{path, section, summary}` | exactly one row per context path; `section` names the body's `## ` heading that explains its effect; non-empty summary |
| `evidence[]` `{id, type, reference, status, detail}` | unique id; non-empty fields; see Evidence |
| `claims[]` `{id, category, text, evidence_ids}` | ≥ 1; unique id; category `SCOPE`, `IMPLEMENTATION`, `TEST`, `SAFETY`, `ARCHITECTURE`, `BUSINESS_RULE`, `REFERENCE`; `text` appears verbatim in the body; cites ≥ 1 known evidence id |
| `body_file` or `body` | exactly one: absolute path to the UTF-8 Markdown body (preferred) or the inline string |
| `remote_update` | see Remote Update |

## Evidence

| Type | Reference | Status |
| --- | --- | --- |
| `DIFF`, `FILE` | a changed path | `INFO` |
| `COMMIT` | a full commit SHA from the context | `INFO` |
| `VALIDATION` | the exact command; detail gives the result | `PASS`, `FAIL`, or `NOT_RUN` |
| `USER` | an explicit user fact, without private content | `INFO` |
| `REMOTE` | proposal metadata read from the platform | `INFO` |

## Body

Raw Markdown: no outer code fence or blank template instructions; no `<!--`, `-->`, `TODO`, `TBD` (case-insensitive, whole word), four or more underscores, `<specific type>`, `<module or path>`, or `<command>`; no repeated `## ` heading.

## Remote Update

`{requested, expected_head_sha, observed_head_sha, status, receipts, error}`: boolean `requested`; *derived* `expected_head_sha` (context head); non-empty `observed_head_sha` (re-read head; the frozen head for a draft); `receipts[]` `{kind, id, url, status}` non-empty; `error` null or non-empty.

- `requested: false`: `NOT_REQUESTED`, no receipts, no error.
- `requested: true`: never `NOT_REQUESTED`; `PLANNED`: no receipts, no error; `UPDATED`: receipts, no error; `PARTIAL`: receipts and error; `BLOCKED` (forced on head drift): no receipts, error.
