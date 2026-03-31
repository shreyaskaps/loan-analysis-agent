# Fix Applied: Remove Debugging Notes from SYSTEM_PROMPT

## Problem
The `SYSTEM_PROMPT` in `agent.py` contained 9 lines of developer debugging notes that were accidentally left in production. These notes were being sent verbatim to Claude on every API call, contaminating the model's understanding of its role.

## Root Cause
Lines 14-23 of the original SYSTEM_PROMPT contained:
```
Looking at the failure pattern, the issue is that `calculate_loan_terms` is never being called — the agent is either asking for uploads when text data is present, or using the wrong tool. The fix needs to:

1. Add `calculate_loan_terms` to the Tool Selection Guide so the agent knows when to use it
2. Clarify that text data is sufficient to trigger this tool (no upload required)

The most appropriate place is in the workflow section (step 2) where other tools are mapped to document types, and in the argument formatting section.

---
```

These are developer notes explaining what needs to be fixed, NOT actual prompt instructions.

## Solution Applied
Removed only those 9 debug lines. The actual prompt content (Prompt B - Granular/Detailed) is fully preserved.

## Verification
✓ All 9 debugging lines removed
✓ SYSTEM_PROMPT now starts with: "You are a loan analysis agent..."
✓ All tool selection guidance preserved
✓ All formatting rules preserved  
✓ All multi-turn memory instructions preserved
✓ All chaining rules preserved
✓ No syntax errors introduced
✓ Agent initializes correctly

## Impact
This fix restores the SYSTEM_PROMPT to the correct "Prompt B" state with:
- Explicit "text data = document, call tools immediately" rule
- Per-argument format rules for correct argument extraction
- Multi-turn memory instruction to prevent forgetting data
- Chaining rule to ensure complete workflows

The removed debugging notes were NOT part of the intended prompt and should never have been sent to the model.
