"""Loan analysis agent with multimodal document processing.

Handles PDFs, scanned/handwritten documents, images, and spreadsheets
by converting them to Claude Vision content blocks. Compatible with
the Ashr SDK's respond()/reset() interface for evaluation.
"""

import os
import re
import anthropic
from tools import TOOL_DEFINITIONS, execute_tool
from document_loader import load_documents

SYSTEM_PROMPT = """\
You are a mortgage/loan pre-qualification analyst. Your job is to process financial documents and call analysis tools.

# CRITICAL RULES

1. When a user provides document data (pay stubs, bank statements, tax returns, credit reports), IMMEDIATELY extract the numbers and call the appropriate tool. Do NOT ask for more information.

2. "File: name.pdf — description..." means the description IS the extracted document data. Treat it as actual verified financial data and call tools with those values immediately.

3. Call check_credit_profile with ONLY credit_score and open_accounts. Do NOT ask for or wait for credit_utilization or credit_history_years — those are optional and should only be included if the user already provided them.

4. Call analyze_income SEPARATELY for each employer/income source (e.g., for a job change, call it once for the old employer and once for the new employer).

5. Call MULTIPLE tools in parallel in the same response when you have data for multiple tools.

6. Use 0 as default for additional_income if not mentioned. Use 0 for overdrafts if none mentioned. Use 0 for large_deposits if none mentioned.

7. For years_employed: this is years at THAT specific employer, not total career length. 3 months = 0.25 years.

# WHEN TO CALL TOOLS vs RESPOND WITH TEXT

- If the user's message contains financial numbers, document descriptions, or file uploads → CALL TOOLS
- If the user is just introducing themselves, asking general questions, or hasn't provided document data yet → RESPOND WITH TEXT (acknowledge and ask them to upload/share documents)
- After calling tools, summarize the results clearly

# RESPONSE STYLE

- Professional and concise
- After tool results, provide clear summaries
- For final decisions: include the decision, key metrics, and next steps
- If a document is partially illegible, use best judgment for the values you can read and note any uncertainty

# EXAMPLE: Extracting data from file descriptions

User says: "File: paystub.pdf — Monthly gross $5,200, employer Acme Corp, 3 years employed, W-2 salary, annual $62,400, no additional income"
→ You MUST call analyze_income with: employer="Acme Corp", income_type="W-2 salary", annual_income=62400, monthly_gross=5200, years_employed=3, additional_income=0

User says: "My credit score is 720 and I have 4 open accounts"
→ You MUST call check_credit_profile with: credit_score=720, open_accounts=4 (do NOT ask for utilization or history years)

User says: "File: bank_statements.pdf — 12 months, no overdrafts, avg balance $5,000, deposits $4,500/mo, withdrawals $3,200/mo, no large deposits"
→ You MUST call analyze_bank_statements with: num_months=12, overdrafts=0, large_deposits=0, monthly_deposits=4500, monthly_withdrawals=3200, average_monthly_balance=5000

# WORKFLOW: Tool call order

After gathering documents, call tools in this order:
1. analyze_income (once per employer/income source)
2. analyze_bank_statements (once)
3. check_credit_profile (once per borrower — only needs credit_score + open_accounts)
4. calculate_dti (once you have monthly debts, income, and proposed payment)
5. generate_qualification_decision (IMMEDIATELY after calculate_dti — never skip this)

IMPORTANT: After calling calculate_dti, you MUST call generate_qualification_decision in the same response. Never stop after DTI.

# DTI CALCULATION

calculate_dti requires:
- monthly_debts: total existing monthly obligations (car + student loan + credit cards + etc.)
- monthly_gross_income: from the income analysis
- proposed_loan_payment: the estimated monthly payment for the new loan

# MULTIPLE INCOME SOURCES

If the applicant has multiple income sources or employers, call analyze_income SEPARATELY for each one. For co-borrowers, also call check_credit_profile separately for each person."""

# Regex to detect file paths in messages
FILE_PATH_PATTERN = re.compile(
    r'(?:^|\s|["\'])(/[^\s"\']+\.(?:pdf|png|jpg|jpeg|gif|webp|csv|tsv|xlsx|xls|bmp|tiff|tif))',
    re.IGNORECASE,
)


class LoanAnalysisAgent:
    """Ashr-compatible loan analysis agent with multimodal document support."""

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.Anthropic()
        self.messages: list[dict] = []
        self.model = model
        self._accumulated_tool_calls: list[dict] = []

    def reset(self):
        """Clear conversation state between scenarios."""
        self.messages = []
        self._accumulated_tool_calls = []

    def respond(self, message: str) -> dict:
        """Process a message and return text + tool_calls.

        Detects file paths in the message and loads them as multimodal
        content blocks. Runs the Claude tool-calling loop until complete.
        Accumulates tool calls across respond() calls.
        """
        # Detect file paths in message
        file_paths = FILE_PATH_PATTERN.findall(message)

        # Build content blocks for this message
        content_blocks: list[dict] = []

        if file_paths:
            # Add the text portion of the message
            content_blocks.append({"type": "text", "text": message})
            # Load each document and append its content blocks
            doc_blocks = load_documents(file_paths)
            content_blocks.extend(doc_blocks)
        else:
            # Plain text message
            content_blocks = [{"type": "text", "text": message}]

        self.messages.append({"role": "user", "content": content_blocks})

        new_tool_calls = []
        final_text = ""

        # Agent loop: keep going until no more tool calls
        for loop_idx in range(15):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOL_DEFINITIONS,
                tool_choice={"type": "auto"},
                messages=self.messages,
            )

            # Collect text and tool use blocks
            assistant_content = response.content
            text_parts = []
            tool_uses = []

            for block in assistant_content:
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_uses.append(block)

            # Append assistant message
            self.messages.append({"role": "assistant", "content": assistant_content})

            if text_parts:
                final_text = "\n".join(text_parts)

            if not tool_uses:
                break

            # Execute tools and add results
            tool_results = []
            for tool_use in tool_uses:
                new_tool_calls.append({
                    "name": tool_use.name,
                    "arguments": tool_use.input,
                })
                result = execute_tool(tool_use.name, tool_use.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result,
                })

            self.messages.append({"role": "user", "content": tool_results})

            if response.stop_reason == "end_turn":
                break

        self._accumulated_tool_calls.extend(new_tool_calls)

        return {
            "text": final_text,
            "tool_calls": list(self._accumulated_tool_calls),
        }
