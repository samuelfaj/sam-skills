---
name: sam-orchestrate-claude
description: "Compatibility entry point for the canonical sam-orchestrate workflow. Use only when existing automation explicitly invokes this legacy skill name."
---

# Sam Orchestrate Compatibility Alias

Read and apply `../sam-orchestrate/SKILL.md` as the complete operating contract.

Do not define routing, verification, delegation, or output policy here. Do not
silently recreate the canonical workflow when that file is unavailable. Stop
and report the missing canonical skill so the installation can be repaired.

Return the same behavior and output as `$sam-orchestrate`.
