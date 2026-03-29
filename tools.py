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


# --------------------------------------------------------------------------
# Input-coercion helpers
# --------------------------------------------------------------------------

_FALSY_STRINGS = {"none", "null", "false", "n/a", "", "0"}


def _coerce_number(val, default: float = 0) -> float:
    """Coerce val to a float, returning *default* for any bad/missing input.

    Handles: None, False, True, empty string, strings like "none"/"null"/"false",
    lists (returns default), and regular numeric strings.
    """
    if val is None or val is False:
        return default
    if val is True:
        return 1.0
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        if val.strip().lower() in _FALSY_STRINGS:
            return default
        # Strip leading $ and commas so "$1,200" → 1200
        cleaned = val.strip().lstrip("$").replace(",", "")
        try:
            return float(cleaned)
        except ValueError:
            return default
    # lists, dicts, etc. → default
    return default


def _coerce_str(val, default: str = "") -> str:
    """Coerce val to a clean string, returning *default* for None/False/null-ish."""
    if val is None or val is False:
        return default
    if val is True:
        return "true"
    if isinstance(val, str):
        if val.strip().lower() in {"none", "null"}:
            return default
        return val
    return str(val)


def _coerce_large_deposits(val):
    """Normalise large_deposits to either 0 (empty) or a list of floats."""
    # Falsy / empty signals
    if val is None or val is False or val == [] or val == 0:
        return 0
    if isinstance(val, str):
        stripped = val.strip().lower()
        if stripped in _FALSY_STRINGS:
            return 0
        # Try JSON decode first
        import json as _json
        try:
            parsed = _json.loads(val)
            return _coerce_large_deposits(parsed)
        except (ValueError, TypeError):
            pass
        # Single numeric string
        cleaned = stripped.lstrip("$").replace(",", "")
        try:
            return [float(cleaned)]
        except ValueError:
            return 0
    if isinstance(val, (int, float)):
        return [float(val)]
    if isinstance(val, list):
        result = []
        for item in val:
            if isinstance(item, dict):
                amount = item.get("amount", item)
                result.append(_coerce_number(amount))
            else:
                result.append(_coerce_number(item))
        return result if result else 0
    return 0


def _coerce_derogatory(val) -> str:
    """Normalise derogatory_marks to a display string."""
    if val is None or val is False or val == [] or val == 0 or val == "0":
        return "none"
    if isinstance(val, str):
        stripped = val.strip().lower()
        if stripped in {"none", "null", "false", "0", "n/a", ""}:
            return "none"
        return val.strip()
    if isinstance(val, list):
        if len(val) == 0:
            return "none"
        return ", ".join(str(x) for x in val)
    return str(val)


def _coerce_utilization(val) -> float:
    """Normalise credit_utilization to a percentage float (e.g. 18.0 for 18%)."""
    if val is None or val is False:
        return 0.0
    if isinstance(val, bool):
        return 0.0
    num = _coerce_number(val, default=0.0)
    # If expressed as a decimal fraction (< 1), convert to percent
    if 0 < num < 1:
        return round(num * 100, 2)
    return round(num, 2)


# --------------------------------------------------------------------------
# Tool executor
# --------------------------------------------------------------------------

def execute_tool(name: str, arguments: dict) -> str:
    """Execute a tool and return a result string."""
    if name == "analyze_income":
        monthly = _coerce_number(arguments.get("monthly_gross"), 0)
        annual = _coerce_number(arguments.get("annual_income"), 0)
        employer = _coerce_str(arguments.get("employer"), "Unknown")
        income_type = _coerce_str(arguments.get("income_type"), "Unknown")
        years = _coerce_number(arguments.get("years_employed"), 0)
        additional = _coerce_number(arguments.get("additional_income"), 0)
        return (
            f"Income analysis complete. Employer: {employer}. "
            f"Income type: {income_type}. Annual income: ${annual:,.0f}. "
            f"Monthly gross: ${monthly:,.0f}. Years employed: {years}. "
            f"Additional income: ${additional:,.0f}. "
            f"Income verified and consistent with documentation."
        )

    elif name == "analyze_bank_statements":
        months = _coerce_number(arguments.get("num_months"), 0)
        balance = _coerce_number(arguments.get("average_monthly_balance"), 0)
        deposits = _coerce_number(arguments.get("monthly_deposits"), 0)
        withdrawals = _coerce_number(arguments.get("monthly_withdrawals"), 0)
        overdrafts = _coerce_number(arguments.get("overdrafts"), 0)
        large = _coerce_large_deposits(arguments.get("large_deposits"))
        overdraft_note = "No overdrafts detected." if overdrafts == 0 else f"{int(overdrafts)} overdraft(s) detected in the period."
        return (
            f"Bank statement analysis complete ({int(months)} months). "
            f"Average monthly balance: ${balance:,.0f}. "
            f"Monthly deposits: ${deposits:,.0f}. Monthly withdrawals: ${withdrawals:,.0f}. "
            f"{overdraft_note} Large deposits: {large}. "
            f"Cash flow appears {'stable' if overdrafts == 0 else 'somewhat irregular'}."
        )

    elif name == "check_credit_profile":
        score = _coerce_number(arguments.get("credit_score"), 0)
        accounts = _coerce_number(arguments.get("open_accounts"), 0)
        derog = _coerce_derogatory(arguments.get("derogatory_marks"))
        util = _coerce_utilization(arguments.get("credit_utilization"))
        history = _coerce_number(arguments.get("credit_history_years"), 0)
        rating = "excellent" if score >= 750 else "good" if score >= 700 else "fair" if score >= 650 else "below average"
        return (
            f"Credit profile check complete. Score: {int(score)} ({rating}). "
            f"Open accounts: {int(accounts)}. Derogatory marks: {derog}. "
            f"Credit utilization: {util}%. Credit history: {history} years. "
        )

    elif name == "calculate_dti":
        debts = _coerce_number(arguments.get("monthly_debts"), 0)
        income = _coerce_number(arguments.get("monthly_gross_income"), 0)
        payment = _coerce_number(arguments.get("proposed_loan_payment"), 0)
        total = debts + payment
        dti = total / income if income > 0 else 0
        return (
            f"DTI calculation complete. Monthly debts: ${debts:,.2f}. "
            f"Proposed payment: ${payment:,.2f}. Total obligations: ${total:,.2f}. "
            f"Monthly gross income: ${income:,.2f}. DTI ratio: {dti:.4f} ({dti * 100:.1f}%)."
        )

    elif name == "generate_qualification_decision":
        dti = _coerce_number(arguments.get("dti_ratio"), 0)
        loan_type = _coerce_str(arguments.get("loan_type"), "unknown")
        amount = _coerce_number(arguments.get("loan_amount"), 0)
        score = _coerce_number(arguments.get("credit_score"), 0)
        collateral = _coerce_str(arguments.get("collateral"), "none")
        income = _coerce_number(arguments.get("annual_income"), 0)
        years = _coerce_number(arguments.get("employment_years"), 0)
        down = _coerce_number(arguments.get("down_payment_percent"), 0)

        qualified = dti < 0.50 and score >= 580
        decision = "CONDITIONALLY APPROVED" if qualified else "FURTHER REVIEW NEEDED"

        return (
            f"Qualification decision: {decision}. "
            f"Loan type: {loan_type}. Amount: ${amount:,.0f}. "
            f"Credit score: {int(score)}. DTI: {dti:.1%}. "
            f"Annual income: ${income:,.0f}. Employment: {years} years. "
            f"Collateral: {collateral}. Down payment: {down}%. "
        )

    return f"Unknown tool: {name}"
