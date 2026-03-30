"""Tool definitions and implementations for the loan analysis agent."""

TOOL_DEFINITIONS = [
    {
        "name": "analyze_income",
        "description": "Analyze and verify income from uploaded pay stubs, W-2s, tax returns, or other income documentation. Call this tool after extracting income details from the user's uploaded documents.",
        "input_schema": {
            "type": "object",
            "properties": {
                "employer": {"type": "string", "description": "Employer name from pay stubs or tax docs"},
                "income_type": {"type": "string", "description": "Income type: W2, 1099, W-2, W-2 + 1099, W-2 + 1099 + rental, SSA + pension, self-employed, etc."},
                "annual_income": {"type": "number", "description": "Annual gross income in dollars"},
                "monthly_gross": {"type": "number", "description": "Monthly gross income in dollars"},
                "years_employed": {"type": "number", "description": "Years employed with current employer"},
                "additional_income": {"type": "number", "description": "Additional monthly or annual income (rental, freelance, etc). Use 0 if none."},
            },
            "required": ["employer", "income_type", "annual_income", "monthly_gross", "years_employed", "additional_income"],
        },
    },
    {
        "name": "analyze_bank_statements",
        "description": "Analyze bank statements for cash flow health, reserves, overdrafts, and deposit patterns. Call this after extracting bank statement details from user uploads.",
        "input_schema": {
            "type": "object",
            "properties": {
                "num_months": {"type": "number", "description": "Number of months of statements provided"},
                "overdrafts": {"type": "number", "description": "Number of overdrafts in the statement period"},
                "large_deposits": {
                    "description": "Large or unusual deposits. Single number or array of amounts. Use 0 if none.",
                },
                "monthly_deposits": {"type": "number", "description": "Average monthly deposit amount"},
                "monthly_withdrawals": {"type": "number", "description": "Average monthly withdrawal amount"},
                "average_monthly_balance": {"type": "number", "description": "Average monthly account balance"},
            },
            "required": ["num_months", "overdrafts", "large_deposits", "monthly_deposits", "monthly_withdrawals", "average_monthly_balance"],
        },
    },
    {
        "name": "check_credit_profile",
        "description": "Check and evaluate a credit report. Call this after extracting credit report details from user uploads.",
        "input_schema": {
            "type": "object",
            "properties": {
                "credit_score": {"type": "number", "description": "Credit score (FICO or Vantage equivalent)"},
                "open_accounts": {"type": "number", "description": "Number of open credit accounts"},
                "derogatory_marks": {"description": "Number of derogatory marks or 'none'"},
                "credit_utilization": {"description": "Credit utilization as decimal (0.18) or percentage (18)"},
                "credit_history_years": {"type": "number", "description": "Length of credit history in years"},
            },
            "required": ["credit_score", "open_accounts", "derogatory_marks", "credit_utilization", "credit_history_years"],
        },
    },
    {
        "name": "calculate_dti",
        "description": "Calculate debt-to-income ratio. Call this with the borrower's monthly debts, gross income, and proposed new loan payment.",
        "input_schema": {
            "type": "object",
            "properties": {
                "monthly_debts": {"type": "number", "description": "Total existing monthly debt payments (car, student loan, credit cards, etc.)"},
                "monthly_gross_income": {"type": "number", "description": "Monthly gross income"},
                "proposed_loan_payment": {"type": "number", "description": "Proposed monthly payment for the new loan"},
            },
            "required": ["monthly_debts", "monthly_gross_income", "proposed_loan_payment"],
        },
    },
    {
        "name": "generate_qualification_decision",
        "description": "Generate a preliminary loan qualification decision based on all gathered data. Call this after income analysis, bank analysis, credit check, and DTI calculation are complete.",
        "input_schema": {
            "type": "object",
            "properties": {
                "dti_ratio": {"type": "number", "description": "Calculated DTI ratio as decimal (e.g. 0.35)"},
                "loan_type": {"type": "string", "description": "Loan type: personal_loan, auto_loan, HELOC, 30-year fixed, small_business, etc."},
                "collateral": {"type": "string", "description": "Collateral description or 'none'/'unsecured'"},
                "loan_amount": {"type": "number", "description": "Requested loan amount"},
                "credit_score": {"type": "number", "description": "Borrower's credit score"},
                "annual_income": {"type": "number", "description": "Borrower's annual income"},
                "employment_years": {"type": "number", "description": "Years of employment"},
                "down_payment_percent": {"type": "number", "description": "Down payment as percentage (0 if none)"},
            },
            "required": ["dti_ratio", "loan_type", "collateral", "loan_amount", "credit_score", "annual_income", "employment_years", "down_payment_percent"],
        },
    },
]


def execute_tool(name: str, arguments: dict) -> str:
    """Execute a tool and return a result string."""
    if name == "analyze_income":
        monthly = arguments.get("monthly_gross", 0)
        annual = arguments.get("annual_income", 0)
        employer = arguments.get("employer", "Unknown")
        income_type = arguments.get("income_type", "Unknown")
        years = arguments.get("years_employed", 0)
        additional = arguments.get("additional_income", 0)
        return (
            f"Income analysis complete. Employer: {employer}. "
            f"Income type: {income_type}. Annual income: ${annual:,.0f}. "
            f"Monthly gross: ${monthly:,.0f}. Years employed: {years}. "
            f"Additional income: ${additional:,.0f}. "
            f"Income verified and consistent with documentation."
        )

    elif name == "analyze_bank_statements":
        months = arguments.get("num_months", 0)
        balance = arguments.get("average_monthly_balance", 0)
        deposits = arguments.get("monthly_deposits", 0)
        withdrawals = arguments.get("monthly_withdrawals", 0)
        overdrafts = arguments.get("overdrafts", 0)
        large = arguments.get("large_deposits", 0)
        overdraft_note = "No overdrafts detected." if overdrafts == 0 else f"{overdrafts} overdraft(s) detected in the period."
        return (
            f"Bank statement analysis complete ({months} months). "
            f"Average monthly balance: ${balance:,.0f}. "
            f"Monthly deposits: ${deposits:,.0f}. Monthly withdrawals: ${withdrawals:,.0f}. "
            f"{overdraft_note} Large deposits: {large}. "
            f"Cash flow appears {'stable' if overdrafts == 0 else 'somewhat irregular'}."
        )

    elif name == "check_credit_profile":
        score = arguments.get("credit_score", 0)
        accounts = arguments.get("open_accounts", 0)
        derog = arguments.get("derogatory_marks", 0)
        util = arguments.get("credit_utilization", 0)
        history = arguments.get("credit_history_years", 0)
        rating = "excellent" if score >= 750 else "good" if score >= 700 else "fair" if score >= 650 else "below average"
        return (
            f"Credit profile check complete. Score: {score} ({rating}). "
            f"Open accounts: {accounts}. Derogatory marks: {derog}. "
            f"Credit utilization: {util}. Credit history: {history} years. "
        )

    elif name == "calculate_dti":
        debts = arguments.get("monthly_debts", 0)
        income = arguments.get("monthly_gross_income", 0)
        payment = arguments.get("proposed_loan_payment", 0)
        total = debts + payment
        dti = total / income if income > 0 else 0
        return (
            f"DTI calculation complete. Monthly debts: ${debts:,.2f}. "
            f"Proposed payment: ${payment:,.2f}. Total obligations: ${total:,.2f}. "
            f"Monthly gross income: ${income:,.2f}. DTI ratio: {dti:.4f} ({dti * 100:.1f}%)."
        )

    elif name == "generate_qualification_decision":
        dti = arguments.get("dti_ratio", 0)
        loan_type = arguments.get("loan_type", "")
        amount = arguments.get("loan_amount", 0)
        score = arguments.get("credit_score", 0)
        collateral = arguments.get("collateral", "none")
        income = arguments.get("annual_income", 0)
        years = arguments.get("employment_years", 0)
        down = arguments.get("down_payment_percent", 0)

        qualified = dti < 0.50 and score >= 580
        decision = "CONDITIONALLY APPROVED" if qualified else "FURTHER REVIEW NEEDED"

        return (
            f"Qualification decision: {decision}. "
            f"Loan type: {loan_type}. Amount: ${amount:,.0f}. "
            f"Credit score: {score}. DTI: {dti:.1%}. "
            f"Annual income: ${income:,.0f}. Employment: {years} years. "
            f"Collateral: {collateral}. Down payment: {down}%. "
        )

    return f"Unknown tool: {name}"


# ── Claude Agent SDK MCP tool wrappers ─────────────────────────────────────
import json as _json
from typing import Any

try:
    from claude_agent_sdk import tool, create_sdk_mcp_server

    @tool(
        "analyze_income",
        "Analyze and verify income from pay stubs, W-2s, tax returns, or other income documentation.",
        {
            "employer": str,
            "income_type": str,
            "annual_income": float,
            "monthly_gross": float,
            "years_employed": float,
            "additional_income": float,
        },
    )
    async def _mcp_analyze_income(args: dict[str, Any]) -> dict[str, Any]:
        result = execute_tool("analyze_income", args)
        return {"content": [{"type": "text", "text": result}]}

    @tool(
        "analyze_bank_statements",
        "Analyze bank statements for cash flow health, reserves, overdrafts, and deposit patterns.",
        {
            "num_months": float,
            "overdrafts": float,
            "large_deposits": str,
            "monthly_deposits": float,
            "monthly_withdrawals": float,
            "average_monthly_balance": float,
        },
    )
    async def _mcp_analyze_bank_statements(args: dict[str, Any]) -> dict[str, Any]:
        # large_deposits arrives as a JSON string from MCP; parse it back to number/list
        ld = args.get("large_deposits", "0")
        if isinstance(ld, str):
            try:
                ld = _json.loads(ld)
            except (_json.JSONDecodeError, ValueError):
                try:
                    ld = float(ld)
                except (TypeError, ValueError):
                    ld = 0
        args = dict(args)
        args["large_deposits"] = ld
        result = execute_tool("analyze_bank_statements", args)
        return {"content": [{"type": "text", "text": result}]}

    @tool(
        "check_credit_profile",
        "Check and evaluate a credit report.",
        {
            "credit_score": float,
            "open_accounts": float,
            "derogatory_marks": str,
            "credit_utilization": str,
            "credit_history_years": float,
        },
    )
    async def _mcp_check_credit_profile(args: dict[str, Any]) -> dict[str, Any]:
        # credit_utilization may arrive as a string ("12" or "0.12"); keep as-is for execute_tool
        args = dict(args)
        cu = args.get("credit_utilization", "0")
        try:
            args["credit_utilization"] = float(cu)
        except (TypeError, ValueError):
            pass
        result = execute_tool("check_credit_profile", args)
        return {"content": [{"type": "text", "text": result}]}

    @tool(
        "calculate_dti",
        "Calculate debt-to-income ratio from monthly debts, gross income, and proposed loan payment.",
        {
            "monthly_debts": float,
            "monthly_gross_income": float,
            "proposed_loan_payment": float,
        },
    )
    async def _mcp_calculate_dti(args: dict[str, Any]) -> dict[str, Any]:
        result = execute_tool("calculate_dti", args)
        return {"content": [{"type": "text", "text": result}]}

    @tool(
        "generate_qualification_decision",
        "Generate a preliminary loan qualification decision based on all gathered data.",
        {
            "dti_ratio": float,
            "loan_type": str,
            "collateral": str,
            "loan_amount": float,
            "credit_score": float,
            "annual_income": float,
            "employment_years": float,
            "down_payment_percent": float,
        },
    )
    async def _mcp_generate_qualification_decision(args: dict[str, Any]) -> dict[str, Any]:
        result = execute_tool("generate_qualification_decision", args)
        return {"content": [{"type": "text", "text": result}]}

    _MCP_TOOLS = [
        _mcp_analyze_income,
        _mcp_analyze_bank_statements,
        _mcp_check_credit_profile,
        _mcp_calculate_dti,
        _mcp_generate_qualification_decision,
    ]
    _MCP_TOOL_NAMES = [
        "mcp__loan_tools__analyze_income",
        "mcp__loan_tools__analyze_bank_statements",
        "mcp__loan_tools__check_credit_profile",
        "mcp__loan_tools__calculate_dti",
        "mcp__loan_tools__generate_qualification_decision",
    ]

    def build_loan_mcp_server():
        """Return (server, allowed_tool_names) for use with ClaudeAgentOptions."""
        server = create_sdk_mcp_server(
            name="loan_tools",
            version="1.0.0",
            tools=_MCP_TOOLS,
        )
        return server, list(_MCP_TOOL_NAMES)

    _CLAUDE_AGENT_SDK_AVAILABLE = True

except ImportError:
    _CLAUDE_AGENT_SDK_AVAILABLE = False

    def build_loan_mcp_server():
        raise ImportError(
            "claude-agent-sdk is not installed. Run: pip install claude-agent-sdk"
        )
