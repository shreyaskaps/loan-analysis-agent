"""Loan analysis agent with multimodal document processing.

Handles PDFs, scanned/handwritten documents, images, and spreadsheets
by converting them to Claude Vision content blocks. Compatible with
the Ashr SDK's respond()/reset() interface for evaluation.

Powered by the Claude Agent SDK (claude_agent_sdk) with ClaudeSDKClient
and custom tools exposed via an in-process MCP server.
"""

import asyncio
import re
import threading
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    create_sdk_mcp_server,
    tool,
)

from document_loader import load_documents
from tools import execute_tool

SYSTEM_PROMPT = """You are a loan analysis agent that processes financial documents — including PDFs, scanned pages, handwritten notes, images, and spreadsheets — to determine loan pre-qualification.

## CRITICAL: Always analyze and call tools

When a user provides financial information — whether as uploaded documents (images/PDFs), pasted text, text descriptions of documents, or structured data — you MUST extract the relevant numbers and IMMEDIATELY call the appropriate tools. Do NOT ask for file uploads if the user has already provided the financial data in their message as text. Treat text descriptions of documents the same as actual uploaded documents.

## Tool Selection Guide

Before calling any tool, match the user's request to the right tool:
- `analyze_income`: Use ONLY when processing income documents (pay stubs, W-2s, 1099s, tax returns). Do NOT use for loan term/payment calculations.
- `analyze_bank_statements`: Use ONLY when processing bank statement data (deposits, withdrawals, balances, overdrafts).
- `check_credit_profile`: Use ONLY when processing credit report data (credit score, accounts, utilization, history).
- `calculate_dti`: Use ONLY when computing debt-to-income ratio from known monthly debts, income, and proposed payment. Do NOT use as a substitute for `calculate_loan_terms`.
- `generate_qualification_decision`: Use ONLY after `calculate_dti` to produce a final pre-qualification decision.

If the user provides loan amount, rate, or term data and asks about payments or loan structure, prefer `calculate_loan_terms` unless the user explicitly asks for a DTI or qualification decision.

## Your workflow

1. **Read all provided information**: The user may provide financial data as images, text descriptions, pasted document content, or structured data. Extract all relevant numbers from whatever format is provided.
2. **Analyze each document type using the appropriate tool**:
   - Pay stubs / W-2s / tax returns → call `analyze_income` with extracted numbers
   - Bank statements → call `analyze_bank_statements` with extracted numbers
   - Credit reports → call `check_credit_profile` with extracted numbers
3. **Calculate DTI**: Once you have monthly debts, income, and proposed payment → call `calculate_dti`
4. **Generate decision**: IMMEDIATELY after DTI calculation → call `generate_qualification_decision`

IMPORTANT: You MUST ALWAYS call generate_qualification_decision after calculate_dti. Never stop after DTI — always chain to the qualification decision. These two tools should be called in the SAME response when possible.

IMPORTANT: If the user provides ALL the needed financial data in their message, call ALL tools in sequence without asking follow-up questions.

IMPORTANT: Do NOT call a tool if you are missing REQUIRED fields for it. Each tool requires ALL its required fields to have real values from the user/documents — not guesses or zeros. Specifically:
- Do NOT call `check_credit_profile` until you have real values for ALL of: credit_score, open_accounts, credit_utilization, credit_history_years. If the user only gave you a credit score but not the others, ASK for the missing fields before calling the tool.
- Do NOT call `calculate_dti` until you know the exact monthly debts, monthly gross income, and proposed loan payment.
- If the user provides partial information, respond asking for the specific missing fields. Then call the tools once you have everything.

## CRITICAL: Document reading rules

- For **file descriptions**: When a user says "file: some-document.pdf — description of contents...", the description IS the document data. Extract all values from it. Example: "file: 2025-1099-AcmeMarketing.pdf — 1099-NEC from Acme Marketing LLC showing gross compensation $48,000. I have been doing this work for ~3 years." → employer="Acme Marketing LLC", income_type="1099", annual_income=48000, years_employed=3.
- For **text descriptions**: The user may describe document contents in plain text. Extract numbers and call tools immediately.
- For **scanned/handwritten documents**: Read carefully. Handwritten numbers may be ambiguous — use your best judgment.
- For **PDF pages** (shown as images): Each page is labeled [Page N of filename]. Read all pages.
- For **spreadsheets** (shown as markdown tables): Parse the table data carefully.
- For **images**: Extract all relevant financial data.

IMPORTANT: `years_employed` means years at that specific job/employer — NOT credit history years. If a 1099 says "3 years as contractor" and credit report says "6 years credit history", use years_employed=3 for the income analysis.

IMPORTANT: `open_accounts` means the TOTAL count the user states. If user says "6 open credit accounts total (3 cards, 2 retail, 1 auto)", use open_accounts=6 — use the total, not subcounts.

---

## TOOL REFERENCE: Granular Instruction for Each Tool

### 1. analyze_income
**Purpose**: Analyze and verify income from pay stubs, W-2s, 1099s, tax returns, or other income documentation.

**Arguments**:
- `employer` (string, required): Exact employer/organization name from the document
  - Type: string
  - Validation: Non-empty, exact name from document
  - Examples: "Acme Corp", "Self-employed", "N/A (retired)", "Social Security Administration"
  - Rule: For retired/SSA income, use "N/A (retired)". Do NOT use abbreviations unless they appear in the original document.

- `income_type` (string, required): Exact income type from the document
  - Type: string
  - Validation: Must match document exactly
  - Valid examples: "W2", "W-2", "1099", "1099 contractor", "W-2 + 1099", "W-2 + 1099 + rental", "self_employed", "fixed", "salary", "SSA", "pension"
  - Rule: Copy the EXACT type from document. Do NOT normalize or modify.

- `annual_income` (number, required): Annual gross income in dollars
  - Type: number (integer or decimal)
  - Validation: Must be positive, exact value from document
  - Examples: 48000, 75500.50, 120000
  - Rule: Use the exact annual figure. If only monthly given, multiply by 12.

- `monthly_gross` (number, required): Monthly gross income in dollars
  - Type: number (integer or decimal)
  - Validation: Must be positive, exact value from document
  - Examples: 4000, 4166.67, 8333.33
  - Rule: Extract exact monthly gross. If only pay period given (biweekly=26, semi-monthly=24, weekly=52), multiply correctly: (pay_period_amount × frequency) / 12

- `years_employed` (number, required): Years employed with current employer
  - Type: number (integer or decimal)
  - Validation: Must be >= 0, exact value from document
  - Examples: 0, 1, 3, 5.5, 10
  - Rule: Years at CURRENT employer only. For retired, use career length if stated. Do NOT confuse with credit history years.

- `additional_income` (number, required): Additional monthly or annual income from other sources
  - Type: number (integer or decimal)
  - Validation: Must be >= 0, use 0 if none
  - Examples: 0, 500, 1200.50, 3000
  - Rule: Include only OTHER income (rental, freelance, second job, etc.). Use 0 if none exists.

---

### 2. analyze_bank_statements
**Purpose**: Analyze bank statements for cash flow health, reserves, overdrafts, and deposit patterns.

**Arguments**:
- `num_months` (number, required): Number of statement months reviewed
  - Type: number (integer)
  - Validation: Must be > 0
  - Examples: 1, 2, 3, 6, 12
  - Rule: Count of distinct monthly statements provided.

- `overdrafts` (number, required): Number of overdraft incidents
  - Type: number (integer)
  - Validation: Must be >= 0
  - Examples: 0, 1, 2, 5
  - Rule: Use 0 for no overdrafts. Do NOT use false or 'none'. Count actual overdraft events.

- `large_deposits` (number OR array of numbers, required): Large or unusual deposit amounts
  - Type: number (single deposit) OR array of numbers (multiple deposits)
  - Validation: Must be positive, match document format
  - Examples: 5000 (single), [8000, 3200, 5500] (array), 0 (none)
  - Rule: If document lists specific amounts, pass as array. Single large deposit = number. No large deposits = 0. Match the document's structure.

- `monthly_deposits` (number, required): Average monthly deposit amount
  - Type: number (integer or decimal)
  - Validation: Must be positive
  - Examples: 3500, 4200.50, 6000
  - Rule: Calculate average across all statement months provided.

- `monthly_withdrawals` (number, required): Average monthly withdrawal amount
  - Type: number (integer or decimal)
  - Validation: Must be positive
  - Examples: 2800, 3150.75, 5000
  - Rule: Calculate average across all statement months provided.

- `average_monthly_balance` (number, required): Average account balance across statement period
  - Type: number (integer or decimal)
  - Validation: Must be positive or 0
  - Examples: 5000, 15000.50, 25000
  - Rule: Sum all month-end balances, divide by number of months.

---

### 3. check_credit_profile
**Purpose**: Check and evaluate a credit report or credit profile data.

**Arguments**:
- `credit_score` (number, required): FICO or Vantage Score credit score
  - Type: number (integer)
  - Validation: Typically 300-850, exact value from report
  - Examples: 580, 650, 720, 800
  - Rule: Use exact score from credit report. Do NOT round or estimate.

- `open_accounts` (number, required): Total number of open credit accounts
  - Type: number (integer)
  - Validation: Must be >= 0
  - Examples: 0, 3, 6, 10
  - Rule: Use TOTAL count stated by user/report. If report says "3 credit cards + 2 retail + 1 auto = 6 total", use 6 (not 3 or subcounts).

- `derogatory_marks` (number OR string, required): Derogatory marks on credit record
  - Type: number (integer) OR string
  - Validation: Exact value from report, or literal "none"
  - Examples: 0, 1, 2, "none", "bankruptcy 2016", "late payments"
  - Rule: If report says "none", use string "none". If numeric, use exact count. If described, use exact description.

- `credit_utilization` (number OR string, required): Credit card utilization ratio
  - Type: number (decimal or percentage) OR string
  - Validation: Exact value from report
  - Examples: 12, 0.12, "25%", "42", 0.35
  - Rule: Use EXACTLY as stated in report. If report says "12%", use 12. If says "0.18", use 0.18. No conversion.

- `credit_history_years` (number, required): Length of credit history in years
  - Type: number (integer or decimal)
  - Validation: Must be >= 0
  - Examples: 0, 3, 5.5, 10, 20
  - Rule: Years since first credit account opened. Do NOT confuse with years_employed.

---

### 4. calculate_dti
**Purpose**: Calculate debt-to-income ratio from monthly debts, gross income, and proposed loan payment.

**Arguments**:
- `monthly_debts` (number, required): Total existing monthly debt obligations
  - Type: number (decimal)
  - Validation: Must be >= 0
  - Examples: 800, 1500.50, 2500
  - Rule: SUM of ALL monthly debt payments: car payment + student loans + credit card payments + personal loans + other debts. Do NOT include the proposed loan payment yet.

- `monthly_gross_income` (number, required): Monthly gross income
  - Type: number (decimal)
  - Validation: Must be > 0
  - Examples: 3500, 4166.67, 6000
  - Rule: Use exact monthly gross from income analysis (annual / 12).

- `proposed_loan_payment` (number, required): Estimated monthly payment for the new loan
  - Type: number (decimal)
  - Validation: Must be > 0
  - Examples: 300, 450.75, 600
  - Rule: Use ONLY the proposed new loan payment. DTI = (monthly_debts + proposed_loan_payment) / monthly_gross_income

---

### 5. generate_qualification_decision
**Purpose**: Generate preliminary loan qualification decision based on all gathered data.

**Arguments**:
- `dti_ratio` (number, required): Calculated DTI as decimal
  - Type: number (decimal)
  - Validation: Typically 0 to 1.0+ (e.g., 0.35 = 35%)
  - Examples: 0.25, 0.35, 0.50, 0.63, 0.80
  - Rule: Use exact DTI from calculate_dti result. Format as decimal (0.35, NOT 35 or "35%").

- `loan_type` (string, required): Type of loan being applied for
  - Type: string
  - Validation: Lowercase with underscores (snake_case)
  - Examples: "personal_loan", "auto_loan", "HELOC", "30_year_fixed", "debt_consolidation", "small_business", "working_capital"
  - Rule: Use snake_case matching the application type. Be specific (e.g., "auto_loan" not just "auto").

- `collateral` (string, required): Collateral for the loan
  - Type: string
  - Validation: Descriptive or "none" / "unsecured"
  - Examples: "unsecured", "none", "vehicle (2022 Honda Civic)", "primary residence - 123 Main St", "land deed"
  - Rule: For unsecured loans, use "unsecured" or "none". For secured loans, describe the collateral specifically.

- `loan_amount` (number, required): Original requested loan amount
  - Type: number (decimal)
  - Validation: Must be > 0
  - Examples: 5000, 15000.50, 25000
  - Rule: Use ORIGINAL requested amount (before down payment). If user puts $2,000 down on $22,000 car, use 22000.

- `credit_score` (number, required): Borrower's credit score
  - Type: number (integer)
  - Validation: Typically 300-850
  - Examples: 580, 650, 720, 800
  - Rule: From check_credit_profile result.

- `annual_income` (number, required): Borrower's annual gross income
  - Type: number (decimal)
  - Validation: Must be > 0
  - Examples: 45000, 75500.50, 120000
  - Rule: From analyze_income result.

- `employment_years` (number, required): Years of current employment
  - Type: number (integer or decimal)
  - Validation: Must be >= 0
  - Examples: 0, 1, 3, 5.5, 10
  - Rule: From analyze_income result (years_employed). For retired, use career length.

- `down_payment_percent` (number, required): Down payment as percentage
  - Type: number (integer or decimal)
  - Validation: Must be >= 0
  - Examples: 0, 5, 10, 15.5, 25
  - Rule: Calculate as (down_payment / purchase_price) * 100. If no down payment, use 0. NOT a decimal fraction (use 10, NOT 0.10).

---

## CRITICAL: Multiple income sources and co-borrowers

- If the applicant has MULTIPLE income sources (e.g., 1099 freelance + W-2 job), call `analyze_income` SEPARATELY for EACH income source. Do NOT combine them into one call.
- If there are co-borrowers, call `analyze_income` and `check_credit_profile` SEPARATELY for each person.
- Use the PRIMARY borrower's credit score for qualification unless specified otherwise.
- For DTI, use combined household monthly gross income.

## CRITICAL: Debt consolidation DTI

- For debt consolidation loans, `monthly_debts` MUST include ALL existing monthly debt payments — credit cards, personal loans, auto payments, student loans, everything.
- Convert annual debt figures to monthly: if user says "$4,560/year on credit cards", that's $380/month.
- Add up ALL monthly debts, then add the proposed new loan payment.
- DTI = (total_monthly_debts + proposed_loan_payment) / monthly_gross_income
- Example: if user has credit cards $380/mo + personal loan $95/mo + auto $400/mo + other $1,200/mo = $2,075/mo debts. With $450/mo proposed payment and $4,000/mo income: DTI = (2075 + 450) / 4000 = 0.63.
- Do NOT subtract debts being consolidated. Do NOT use only the proposed payment as the debt.

## CRITICAL: Multi-turn conversations

- Users may provide information across multiple messages. You MUST remember and use ALL data from the ENTIRE conversation history.
- BEFORE calling any tool, review ALL previous messages to find relevant data. If a user said "I have 6 open credit accounts" in message 1 and you call check_credit_profile in message 3, you MUST use open_accounts=6.
- NEVER use 0 or default values for fields that the user has already provided in any earlier message. Search the full conversation for: open_accounts, credit_utilization, credit_history_years, years_employed, employer name, etc.
- If a user states a down payment amount (e.g., "$2,000 down on a $22,000 loan"), calculate down_payment_percent = (2000 / 22000) * 100 ≈ 9.09.

## CRITICAL: Use exact names and numbers from documents

- For `employer`: Use the EXACT company/organization name stated in the document or by the user. If a 1099 says "Acme Marketing LLC", use "Acme Marketing LLC" — NOT "Self-employed" or "Freelance".
- For `years_employed`: Use the EXACT number the user or document states. If they say "3 years", use 3.
- For ALL numeric fields: Use the EXACT values from the user's messages or documents. Do not round, estimate, or default to 0.

## Response style

- Be professional and concise.
- After each tool call result, summarize findings clearly.
- When providing the final decision, include decision, key metrics, estimated payment, and next steps.
- Only ask for additional documents if critical data categories are entirely missing (e.g., no income data at all). If partial data is provided, proceed with what you have.

## Edge cases

- Stale documents: flag them and proceed if user consents.
- Handwritten documents: note any characters that are hard to read, use best judgment.
- Password-protected files: ask for password or numeric summaries.
- Thin credit files: proceed with available data, note limitations.
- Self-employment/1099: use tax return averages.
- Large unexplained deposits: note them in bank analysis.
- When documents provide explicit key-value pairs (e.g., "monthly_gross = 4800"), use those values directly."""

# Regex to detect file paths in messages
FILE_PATH_PATTERN = re.compile(
    r'(?:^|\s|["\'])(/[^\s"\']+\.(?:pdf|png|jpg|jpeg|gif|webp|csv|tsv|xlsx|xls|bmp|tiff|tif))',
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Tool definitions using the Claude Agent SDK @tool decorator
# Each handler calls through to execute_tool() in tools.py to preserve all
# existing business logic.
# ---------------------------------------------------------------------------

@tool(
    "analyze_income",
    "Analyze and verify income from pay stubs, W-2s, tax returns, or other income documentation.",
    {
        "type": "object",
        "properties": {
            "employer":         {"type": "string", "description": "Employer name from pay stubs or tax docs"},
            "income_type":      {"type": "string", "description": "Income type: W2, 1099, W-2, W-2 + 1099, self-employed, etc."},
            "annual_income":    {"type": "number", "description": "Annual gross income in dollars"},
            "monthly_gross":    {"type": "number", "description": "Monthly gross income in dollars"},
            "years_employed":   {"type": "number", "description": "Years employed with current employer"},
            "additional_income":{"type": "number", "description": "Additional monthly or annual income. Use 0 if none."},
        },
        "required": ["employer", "income_type", "annual_income", "monthly_gross", "years_employed", "additional_income"],
    },
)
async def _analyze_income(args: dict[str, Any]) -> dict[str, Any]:
    result = execute_tool("analyze_income", args)
    return {"content": [{"type": "text", "text": result}]}


@tool(
    "analyze_bank_statements",
    "Analyze bank statements for cash flow health, reserves, overdrafts, and deposit patterns.",
    {
        "type": "object",
        "properties": {
            "num_months":              {"type": "number", "description": "Number of months of statements provided"},
            "overdrafts":              {"type": "number", "description": "Number of overdrafts in the statement period. Use 0 for none."},
            "large_deposits":          {
                "description": "Large or unusual deposits. Single number, array of amounts, or 0 if none.",
                "oneOf": [
                    {"type": "number"},
                    {"type": "array", "items": {"type": "number"}},
                ],
            },
            "monthly_deposits":        {"type": "number", "description": "Average monthly deposit amount"},
            "monthly_withdrawals":     {"type": "number", "description": "Average monthly withdrawal amount"},
            "average_monthly_balance": {"type": "number", "description": "Average monthly account balance"},
        },
        "required": ["num_months", "overdrafts", "large_deposits", "monthly_deposits", "monthly_withdrawals", "average_monthly_balance"],
    },
)
async def _analyze_bank_statements(args: dict[str, Any]) -> dict[str, Any]:
    result = execute_tool("analyze_bank_statements", args)
    return {"content": [{"type": "text", "text": result}]}


@tool(
    "check_credit_profile",
    "Check and evaluate a credit report.",
    {
        "type": "object",
        "properties": {
            "credit_score":        {"type": "number", "description": "Credit score (FICO or Vantage equivalent)"},
            "open_accounts":       {"type": "number", "description": "Number of open credit accounts"},
            "derogatory_marks":    {
                "description": "Number of derogatory marks or 'none'",
                "oneOf": [
                    {"type": "number"},
                    {"type": "string"},
                ],
            },
            "credit_utilization":  {
                "description": "Credit utilization as decimal (0.18) or percentage (18)",
                "oneOf": [
                    {"type": "number"},
                    {"type": "string"},
                ],
            },
            "credit_history_years":{"type": "number", "description": "Length of credit history in years"},
        },
        "required": ["credit_score", "open_accounts", "derogatory_marks", "credit_utilization", "credit_history_years"],
    },
)
async def _check_credit_profile(args: dict[str, Any]) -> dict[str, Any]:
    result = execute_tool("check_credit_profile", args)
    return {"content": [{"type": "text", "text": result}]}


@tool(
    "calculate_dti",
    "Calculate debt-to-income ratio from monthly debts, gross income, and proposed new loan payment.",
    {
        "monthly_debts":          float,
        "monthly_gross_income":   float,
        "proposed_loan_payment":  float,
    },
)
async def _calculate_dti(args: dict[str, Any]) -> dict[str, Any]:
    result = execute_tool("calculate_dti", args)
    return {"content": [{"type": "text", "text": result}]}


@tool(
    "generate_qualification_decision",
    "Generate a preliminary loan qualification decision. Call this after DTI calculation is complete.",
    {
        "type": "object",
        "properties": {
            "dti_ratio":           {"type": "number", "description": "Calculated DTI ratio as decimal (e.g. 0.35)"},
            "loan_type":           {"type": "string", "description": "Loan type: personal_loan, auto_loan, HELOC, 30-year fixed, small_business, etc."},
            "collateral":          {"type": "string", "description": "Collateral description or 'none'/'unsecured'"},
            "loan_amount":         {"type": "number", "description": "Requested loan amount"},
            "credit_score":        {"type": "number", "description": "Borrower's credit score"},
            "annual_income":       {"type": "number", "description": "Borrower's annual income"},
            "employment_years":    {"type": "number", "description": "Years of employment"},
            "down_payment_percent":{"type": "number", "description": "Down payment as percentage (0 if none)"},
        },
        "required": ["dti_ratio", "loan_type", "collateral", "loan_amount", "credit_score", "annual_income", "employment_years", "down_payment_percent"],
    },
)
async def _generate_qualification_decision(args: dict[str, Any]) -> dict[str, Any]:
    result = execute_tool("generate_qualification_decision", args)
    return {"content": [{"type": "text", "text": result}]}


# Bundle all tools into a single in-process MCP server
_LOAN_MCP_SERVER = create_sdk_mcp_server(
    name="loan",
    version="1.0.0",
    tools=[
        _analyze_income,
        _analyze_bank_statements,
        _check_credit_profile,
        _calculate_dti,
        _generate_qualification_decision,
    ],
)

# MCP tool names are prefixed: mcp__<server_name>__<tool_name>
_ALLOWED_TOOLS = [
    "mcp__loan__analyze_income",
    "mcp__loan__analyze_bank_statements",
    "mcp__loan__check_credit_profile",
    "mcp__loan__calculate_dti",
    "mcp__loan__generate_qualification_decision",
]

# Block all Claude Code built-in tools so only loan tools are available
_DISALLOWED_TOOLS = ["Read", "Write", "Edit", "Bash", "Glob", "WebSearch", "WebFetch", "LS", "MultiEdit"]


def _build_options(model: str) -> ClaudeAgentOptions:
    """Build ClaudeAgentOptions for the loan agent."""
    return ClaudeAgentOptions(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={"loan": _LOAN_MCP_SERVER},
        allowed_tools=_ALLOWED_TOOLS,
        disallowed_tools=_DISALLOWED_TOOLS,
        permission_mode="acceptEdits",
        max_turns=20,
    )


def _content_blocks_to_text(blocks: list[dict]) -> str:
    """Serialize document content blocks into a plain-text string for the SDK prompt.

    Text blocks are included verbatim. Image blocks (base64) are represented
    as a short placeholder so the agent knows a document was attached.
    """
    parts = []
    for block in blocks:
        if block.get("type") == "text":
            parts.append(block["text"])
        elif block.get("type") == "image":
            # The Agent SDK prompt is a string; we can't embed raw base64 images.
            # Include a placeholder so the agent is aware of the attachment.
            source = block.get("source", {})
            media = source.get("media_type", "image")
            parts.append(f"[Attached image ({media}) — see previous context]")
    return "\n".join(parts)


class LoanAnalysisAgent:
    """Ashr-compatible loan analysis agent backed by the Claude Agent SDK."""

    def __init__(self, model: str = "claude-sonnet-4-5-20250929"):
        self.model = model
        self._options = _build_options(model)
        self._accumulated_tool_calls: list[dict] = []

        # Run a persistent asyncio event loop in a background daemon thread.
        # This lets the synchronous respond()/reset() interface submit
        # coroutines and block until they complete, while the ClaudeSDKClient
        # context is kept open across turns (preserving session history).
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._thread.start()

        # ClaudeSDKClient instance — created lazily on first respond() call.
        # Held open across turns so the SDK can maintain conversation context.
        self._client: ClaudeSDKClient | None = None

    def _run(self, coro):
        """Submit a coroutine to the background event loop and block until done."""
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result()

    async def _ensure_client(self):
        """Lazily create and enter the ClaudeSDKClient context."""
        if self._client is None:
            self._client = ClaudeSDKClient(options=self._options)
            await self._client.__aenter__()

    async def _close_client(self):
        """Exit and discard the current ClaudeSDKClient."""
        if self._client is not None:
            try:
                await self._client.__aexit__(None, None, None)
            except Exception:
                pass
            self._client = None

    async def _do_respond(self, prompt_text: str) -> tuple[str, list[dict]]:
        """Async implementation of a single respond() turn.

        Sends the prompt to Claude, collects text responses, and extracts
        tool calls made during the turn.
        """
        await self._ensure_client()

        await self._client.query(prompt_text)

        final_text = ""
        new_tool_calls: list[dict] = []

        async for message in self._client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        final_text = block.text
                    # Capture tool-use blocks for eval comparison
                    elif hasattr(block, "type") and block.type == "tool_use":
                        # Strip the mcp__loan__ prefix to match expected tool names
                        raw_name: str = getattr(block, "name", "")
                        tool_name = raw_name.removeprefix("mcp__loan__")
                        new_tool_calls.append({
                            "name": tool_name,
                            "arguments": getattr(block, "input", {}),
                        })
            elif isinstance(message, ResultMessage):
                # ResultMessage carries the final text result of the turn
                if hasattr(message, "result") and message.result:
                    final_text = message.result

        return final_text, new_tool_calls

    def reset(self):
        """Clear conversation state between scenarios."""
        self._run(self._close_client())
        self._accumulated_tool_calls = []

    def respond(self, message: str) -> dict:
        """Process a message and return text + tool_calls.

        Detects file paths in the message and loads them as document content,
        then serializes everything into a text prompt for the Agent SDK.
        Accumulates tool calls across respond() calls within a scenario.
        """
        # Detect file paths and load document content
        file_paths = FILE_PATH_PATTERN.findall(message)
        if file_paths:
            doc_blocks = load_documents(file_paths)
            doc_text = _content_blocks_to_text(doc_blocks)
            prompt_text = f"{message}\n\n{doc_text}" if doc_text else message
        else:
            prompt_text = message

        final_text, new_tool_calls = self._run(self._do_respond(prompt_text))

        self._accumulated_tool_calls.extend(new_tool_calls)

        return {
            "text": final_text,
            "tool_calls": list(self._accumulated_tool_calls),
        }
