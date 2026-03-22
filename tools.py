"""Tool definitions and implementations for the loan analysis agent."""

from typing import Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require(arguments: dict, *fields: str) -> list[str]:
    """Return a list of missing required field names."""
    return [f for f in fields if arguments.get(f) is None]


def _positive(value: Any, name: str) -> str | None:
    """Return an error string if value is not a positive number, else None."""
    try:
        if float(value) <= 0:
            return f"'{name}' must be a positive number, got {value!r}"
    except (TypeError, ValueError):
        return f"'{name}' must be a number, got {value!r}"
    return None


def _non_negative(value: Any, name: str) -> str | None:
    """Return an error string if value is negative or non-numeric, else None."""
    try:
        if float(value) < 0:
            return f"'{name}' must be zero or positive, got {value!r}"
    except (TypeError, ValueError):
        return f"'{name}' must be a number, got {value!r}"
    return None


def _collect_errors(*checks: str | None) -> list[str]:
    return [c for c in checks if c is not None]


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "name": "analyze_income",
        "description": (
            "Analyze and verify income from pay stubs, W-2s, 1099s, tax returns, or any "
            "other income documentation. Call this tool ONLY when the user has provided "
            "income documents or income figures (employer name, income type, annual/monthly "
            "amounts, years employed). Do NOT call this tool for loan payment calculations, "
            "DTI calculations, or anything unrelated to verifying the borrower's income."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "employer": {
                    "type": "string",
                    "description": "Employer name from pay stubs or tax documents. Use 'Self-employed' or 'Multiple' where appropriate.",
                },
                "income_type": {
                    "type": "string",
                    "description": (
                        "Income classification. Examples: 'W-2', '1099', 'W-2 + 1099', "
                        "'W-2 + rental', 'SSA + pension', 'self-employed', 'rental only'."
                    ),
                },
                "annual_income": {
                    "type": "number",
                    "description": "Total annual gross income in dollars (must be > 0).",
                },
                "monthly_gross": {
                    "type": "number",
                    "description": "Monthly gross income in dollars (must be > 0). Should equal annual_income / 12.",
                },
                "years_employed": {
                    "type": "number",
                    "description": "Years with current employer or in current self-employment (must be >= 0).",
                },
                "additional_income": {
                    "type": "number",
                    "description": (
                        "Additional monthly income from secondary sources such as rental, "
                        "freelance, alimony, or pension. Use 0 if none."
                    ),
                },
            },
            "required": [
                "employer",
                "income_type",
                "annual_income",
                "monthly_gross",
                "years_employed",
                "additional_income",
            ],
        },
    },
    {
        "name": "analyze_bank_statements",
        "description": (
            "Analyze bank statements to assess cash flow health, reserve levels, overdraft "
            "history, and deposit patterns. Call this tool ONLY when the user has provided "
            "bank statement data (balances, deposits, withdrawals, overdraft counts). "
            "Do NOT call this tool for income verification, credit checks, or loan calculations."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "num_months": {
                    "type": "number",
                    "description": "Number of months of bank statements provided (must be >= 1).",
                },
                "overdrafts": {
                    "type": "number",
                    "description": "Total number of overdraft events across all provided statements (must be >= 0).",
                },
                "large_deposits": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": (
                        "List of large or unusual one-time deposit amounts in dollars. "
                        "Use an empty array [] if there are none. Each amount must be > 0."
                    ),
                },
                "monthly_deposits": {
                    "type": "number",
                    "description": "Average total deposits per month across the statement period (must be > 0).",
                },
                "monthly_withdrawals": {
                    "type": "number",
                    "description": "Average total withdrawals per month across the statement period (must be > 0).",
                },
                "average_monthly_balance": {
                    "type": "number",
                    "description": "Average end-of-month account balance across the statement period (must be >= 0).",
                },
            },
            "required": [
                "num_months",
                "overdrafts",
                "large_deposits",
                "monthly_deposits",
                "monthly_withdrawals",
                "average_monthly_balance",
            ],
        },
    },
    {
        "name": "check_credit_profile",
        "description": (
            "Evaluate a borrower's credit report. Call this tool ONLY when the user has "
            "provided credit report data (credit score, account counts, derogatory marks, "
            "utilization, history length). Do NOT call this tool for income, bank, or loan "
            "payment analysis."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "credit_score": {
                    "type": "number",
                    "description": "FICO or VantageScore credit score (valid range: 300–850).",
                },
                "open_accounts": {
                    "type": "number",
                    "description": "Number of currently open credit accounts (must be >= 0).",
                },
                "derogatory_marks": {
                    "type": "number",
                    "description": "Number of derogatory marks (collections, charge-offs, bankruptcies, etc.). Use 0 if none.",
                },
                "credit_utilization": {
                    "type": "number",
                    "description": (
                        "Revolving credit utilization as a decimal between 0 and 1 "
                        "(e.g. 0.18 for 18%). Do NOT pass a percentage integer."
                    ),
                },
                "credit_history_years": {
                    "type": "number",
                    "description": "Length of credit history in years (must be >= 0).",
                },
            },
            "required": [
                "credit_score",
                "open_accounts",
                "derogatory_marks",
                "credit_utilization",
                "credit_history_years",
            ],
        },
    },
    {
        "name": "calculate_dti",
        "description": (
            "Calculate the borrower's debt-to-income (DTI) ratio from known monthly debt "
            "obligations, gross income, and the proposed new loan payment. Call this tool "
            "ONLY after income has been verified (analyze_income) and you have a proposed "
            "monthly payment figure. Do NOT use this tool to calculate loan payment amounts "
            "or loan terms — use calculate_loan_terms for that. The DTI result from this "
            "tool should be passed directly into generate_qualification_decision."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "monthly_debts": {
                    "type": "number",
                    "description": (
                        "Sum of all existing recurring monthly debt payments: car loans, "
                        "student loans, minimum credit card payments, child support, etc. "
                        "Do NOT include the proposed new loan payment here. Use 0 if none."
                    ),
                },
                "monthly_gross_income": {
                    "type": "number",
                    "description": "Borrower's monthly gross income in dollars (must be > 0).",
                },
                "proposed_loan_payment": {
                    "type": "number",
                    "description": (
                        "The proposed monthly payment for the new loan being evaluated "
                        "(must be > 0). Use the output of calculate_loan_terms if available."
                    ),
                },
            },
            "required": ["monthly_debts", "monthly_gross_income", "proposed_loan_payment"],
        },
    },
    {
        "name": "calculate_loan_terms",
        "description": (
            "Calculate monthly payment, total interest, and total cost for a proposed loan "
            "given a principal amount, annual interest rate, and loan term. Call this tool "
            "whenever the user provides loan parameters (amount, rate, term/duration) and "
            "wants to know payment amounts, total cost, or loan structure — even if the data "
            "is provided as plain text. Do NOT ask for a file upload before calling this tool. "
            "Do NOT substitute analyze_income or calculate_dti for this tool. Call this tool "
            "BEFORE calculate_dti so the monthly payment is known."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "loan_amount": {
                    "type": "number",
                    "description": "Principal loan amount in dollars (must be > 0).",
                },
                "annual_interest_rate": {
                    "type": "number",
                    "description": (
                        "Annual interest rate as a decimal between 0 and 1 "
                        "(e.g. 0.065 for 6.5%). Do NOT pass a percentage integer."
                    ),
                },
                "loan_term_months": {
                    "type": "number",
                    "description": (
                        "Loan repayment term in months (must be > 0). "
                        "Convert years to months before passing: 30 years = 360 months."
                    ),
                },
                "loan_type": {
                    "type": "string",
                    "description": (
                        "Loan product type. Examples: 'personal_loan', 'auto_loan', "
                        "'HELOC', '30-year fixed mortgage', 'small_business'. "
                        "Used for context in the result summary."
                    ),
                },
            },
            "required": ["loan_amount", "annual_interest_rate", "loan_term_months", "loan_type"],
        },
    },
    {
        "name": "generate_qualification_decision",
        "description": (
            "Generate a preliminary loan pre-qualification decision by combining all "
            "previously gathered data points. Call this tool ONLY after ALL of the following "
            "have been completed: analyze_income, analyze_bank_statements, check_credit_profile, "
            "calculate_dti (and calculate_loan_terms if applicable). Do NOT call this tool "
            "before DTI is known. This tool produces the final APPROVED / FURTHER REVIEW "
            "decision and must be the last tool called in the workflow."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "dti_ratio": {
                    "type": "number",
                    "description": (
                        "DTI ratio as a decimal (e.g. 0.35 for 35%). "
                        "Use the exact value returned by calculate_dti."
                    ),
                },
                "loan_type": {
                    "type": "string",
                    "description": "Loan product type (e.g. 'personal_loan', 'auto_loan', '30-year fixed mortgage').",
                },
                "collateral": {
                    "type": "string",
                    "description": "Description of collateral (e.g. '2022 Toyota Camry', 'primary residence'). Use 'none' for unsecured loans.",
                },
                "loan_amount": {
                    "type": "number",
                    "description": "Requested loan amount in dollars (must be > 0).",
                },
                "credit_score": {
                    "type": "number",
                    "description": "Borrower's credit score as returned by check_credit_profile (300–850).",
                },
                "annual_income": {
                    "type": "number",
                    "description": "Borrower's annual gross income as returned by analyze_income (must be > 0).",
                },
                "employment_years": {
                    "type": "number",
                    "description": "Years of employment as returned by analyze_income (must be >= 0).",
                },
                "down_payment_percent": {
                    "type": "number",
                    "description": "Down payment as a percentage of the purchase price (e.g. 20 for 20%). Use 0 if not applicable.",
                },
            },
            "required": [
                "dti_ratio",
                "loan_type",
                "collateral",
                "loan_amount",
                "credit_score",
                "annual_income",
                "employment_years",
                "down_payment_percent",
            ],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def _tool_analyze_income(arguments: dict) -> str:
    missing = _require(arguments, "employer", "income_type", "annual_income", "monthly_gross", "years_employed", "additional_income")
    if missing:
        return f"ERROR: analyze_income is missing required fields: {', '.join(missing)}."

    errors = _collect_errors(
        _positive(arguments["annual_income"], "annual_income"),
        _positive(arguments["monthly_gross"], "monthly_gross"),
        _non_negative(arguments["years_employed"], "years_employed"),
        _non_negative(arguments["additional_income"], "additional_income"),
    )
    if errors:
        return "ERROR: analyze_income received invalid values — " + "; ".join(errors) + "."

    annual = float(arguments["annual_income"])
    monthly = float(arguments["monthly_gross"])
    additional = float(arguments["additional_income"])
    years = float(arguments["years_employed"])
    employer = str(arguments["employer"]).strip() or "Unknown"
    income_type = str(arguments["income_type"]).strip() or "Unknown"

    # Consistency check: monthly * 12 should be within 5 % of annual
    if abs(monthly * 12 - annual) / annual > 0.05:
        consistency_note = (
            f"WARNING: monthly_gross (${monthly:,.0f}) × 12 = ${monthly * 12:,.0f}, "
            f"which differs from annual_income (${annual:,.0f}) by more than 5%. "
            "Verify figures against source documents."
        )
    else:
        consistency_note = "Monthly and annual figures are consistent."

    stability = "strong" if years >= 2 else "limited (under 2 years)"

    return (
        f"Income analysis complete. "
        f"Employer: {employer}. "
        f"Income type: {income_type}. "
        f"Annual gross income: ${annual:,.0f}. "
        f"Monthly gross income: ${monthly:,.0f}. "
        f"Additional monthly income: ${additional:,.0f}. "
        f"Years employed: {years:.1f} (employment stability: {stability}). "
        f"{consistency_note}"
    )


def _tool_analyze_bank_statements(arguments: dict) -> str:
    missing = _require(arguments, "num_months", "overdrafts", "large_deposits", "monthly_deposits", "monthly_withdrawals", "average_monthly_balance")
    if missing:
        return f"ERROR: analyze_bank_statements is missing required fields: {', '.join(missing)}."

    errors = _collect_errors(
        _positive(arguments["num_months"], "num_months"),
        _non_negative(arguments["overdrafts"], "overdrafts"),
        _positive(arguments["monthly_deposits"], "monthly_deposits"),
        _positive(arguments["monthly_withdrawals"], "monthly_withdrawals"),
        _non_negative(arguments["average_monthly_balance"], "average_monthly_balance"),
    )
    if errors:
        return "ERROR: analyze_bank_statements received invalid values — " + "; ".join(errors) + "."

    # Normalise large_deposits to a list of floats
    raw_large = arguments["large_deposits"]
    if raw_large is None:
        large_deposits: list[float] = []
    elif isinstance(raw_large, (int, float)):
        large_deposits = [float(raw_large)] if float(raw_large) > 0 else []
    elif isinstance(raw_large, list):
        large_deposits = [float(x) for x in raw_large if x is not None and float(x) > 0]
    else:
        return f"ERROR: analyze_bank_statements — 'large_deposits' must be a number or array, got {type(raw_large).__name__}."

    months = float(arguments["num_months"])
    overdrafts = int(arguments["overdrafts"])
    deposits = float(arguments["monthly_deposits"])
    withdrawals = float(arguments["monthly_withdrawals"])
    balance = float(arguments["average_monthly_balance"])

    net_monthly = deposits - withdrawals
    if overdrafts == 0:
        overdraft_note = "No overdrafts detected."
        cash_flow_rating = "stable"
    elif overdrafts <= 2:
        overdraft_note = f"{overdrafts} overdraft(s) detected — minor concern."
        cash_flow_rating = "slightly irregular"
    else:
        overdraft_note = f"{overdrafts} overdraft(s) detected — significant concern."
        cash_flow_rating = "irregular"

    if large_deposits:
        large_note = f"Large/unusual deposits: {len(large_deposits)} totalling ${sum(large_deposits):,.0f} — source documentation may be required."
    else:
        large_note = "No large or unusual deposits identified."

    return (
        f"Bank statement analysis complete ({months:.0f} months reviewed). "
        f"Average monthly balance: ${balance:,.0f}. "
        f"Average monthly deposits: ${deposits:,.0f}. "
        f"Average monthly withdrawals: ${withdrawals:,.0f}. "
        f"Net monthly cash flow: ${net_monthly:,.0f}. "
        f"{overdraft_note} "
        f"{large_note} "
        f"Overall cash flow assessment: {cash_flow_rating}."
    )


def _tool_check_credit_profile(arguments: dict) -> str:
    missing = _require(arguments, "credit_score", "open_accounts", "derogatory_marks", "credit_utilization", "credit_history_years")
    if missing:
        return f"ERROR: check_credit_profile is missing required fields: {', '.join(missing)}."

    errors = _collect_errors(
        _non_negative(arguments["credit_score"], "credit_score"),
        _non_negative(arguments["open_accounts"], "open_accounts"),
        _non_negative(arguments["derogatory_marks"], "derogatory_marks"),
        _non_negative(arguments["credit_utilization"], "credit_utilization"),
        _non_negative(arguments["credit_history_years"], "credit_history_years"),
    )
    if errors:
        return "ERROR: check_credit_profile received invalid values — " + "; ".join(errors) + "."

    score = float(arguments["credit_score"])
    accounts = int(arguments["open_accounts"])
    derog = float(arguments["derogatory_marks"])
    util = float(arguments["credit_utilization"])
    history = float(arguments["credit_history_years"])

    # Guard: score out of realistic range
    if not (300 <= score <= 850):
        return f"ERROR: check_credit_profile — credit_score {score} is outside the valid range (300–850)."

    # Guard: utilization looks like it was passed as a percentage integer
    if util > 1:
        return (
            f"ERROR: check_credit_profile — credit_utilization must be a decimal (e.g. 0.18), "
            f"but received {util}. Convert to decimal before calling this tool."
        )

    if score >= 750:
        rating = "excellent"
    elif score >= 700:
        rating = "good"
    elif score >= 650:
        rating = "fair"
    elif score >= 580:
        rating = "below average"
    else:
        rating = "poor"

    util_note = (
        "Low utilization — positive signal."
        if util <= 0.30
        else "High utilization — may negatively impact qualification."
    )

    derog_note = (
        "No derogatory marks — positive signal."
        if derog == 0
        else f"{derog:.0f} derogatory mark(s) — will require underwriter review."
    )

    return (
        f"Credit profile check complete. "
        f"Credit score: {score:.0f} ({rating}). "
        f"Open accounts: {accounts}. "
        f"Credit history: {history:.1f} years. "
        f"Credit utilization: {util:.1%}. {util_note} "
        f"{derog_note}"
    )


def _tool_calculate_dti(arguments: dict) -> str:
    missing = _require(arguments, "monthly_debts", "monthly_gross_income", "proposed_loan_payment")
    if missing:
        return f"ERROR: calculate_dti is missing required fields: {', '.join(missing)}."

    errors = _collect_errors(
        _non_negative(arguments["monthly_debts"], "monthly_debts"),
        _positive(arguments["monthly_gross_income"], "monthly_gross_income"),
        _positive(arguments["proposed_loan_payment"], "proposed_loan_payment"),
    )
    if errors:
        return "ERROR: calculate_dti received invalid values — " + "; ".join(errors) + "."

    debts = float(arguments["monthly_debts"])
    income = float(arguments["monthly_gross_income"])
    payment = float(arguments["proposed_loan_payment"])

    total_obligations = debts + payment
    dti = total_obligations / income

    if dti <= 0.36:
        dti_assessment = "strong — well within conventional lending guidelines"
    elif dti <= 0.43:
        dti_assessment = "acceptable — within FHA/conventional limits"
    elif dti <= 0.50:
        dti_assessment = "elevated — at the upper boundary for most loan programs"
    else:
        dti_assessment = "high — exceeds standard thresholds; approval unlikely without compensating factors"

    return (
        f"DTI calculation complete. "
        f"Existing monthly debt obligations: ${debts:,.2f}. "
        f"Proposed new loan payment: ${payment:,.2f}. "
        f"Total monthly obligations: ${total_obligations:,.2f}. "
        f"Monthly gross income: ${income:,.2f}. "
        f"DTI ratio: {dti:.4f} ({dti:.1%}). "
        f"Assessment: {dti_assessment}."
    )


def _tool_calculate_loan_terms(arguments: dict) -> str:
    missing = _require(arguments, "loan_amount", "annual_interest_rate", "loan_term_months", "loan_type")
    if missing:
        return f"ERROR: calculate_loan_terms is missing required fields: {', '.join(missing)}."

    errors = _collect_errors(
        _positive(arguments["loan_amount"], "loan_amount"),
        _non_negative(arguments["annual_interest_rate"], "annual_interest_rate"),
        _positive(arguments["loan_term_months"], "loan_term_months"),
    )
    if errors:
        return "ERROR: calculate_loan_terms received invalid values — " + "; ".join(errors) + "."

    principal = float(arguments["loan_amount"])
    annual_rate = float(arguments["annual_interest_rate"])
    term_months = int(arguments["loan_term_months"])
    loan_type = str(arguments["loan_type"]).strip() or "unspecified"

    # Guard: rate looks like it was passed as a percentage integer
    if annual_rate > 1:
        return (
            f"ERROR: calculate_loan_terms — annual_interest_rate must be a decimal (e.g. 0.065 for 6.5%), "
            f"but received {annual_rate}. Convert to decimal before calling this tool."
        )

    monthly_rate = annual_rate / 12

    if monthly_rate == 0:
        # Zero-interest loan
        monthly_payment = principal / term_months
        total_paid = principal
        total_interest = 0.0
    else:
        # Standard amortisation formula
        monthly_payment = principal * (monthly_rate * (1 + monthly_rate) ** term_months) / ((1 + monthly_rate) ** term_months - 1)
        total_paid = monthly_payment * term_months
        total_interest = total_paid - principal

    years = term_months / 12
    term_display = f"{term_months} months ({years:.1f} years)" if term_months % 12 != 0 else f"{term_months} months ({int(years)} years)"

    return (
        f"Loan term calculation complete. "
        f"Loan type: {loan_type}. "
        f"Principal: ${principal:,.2f}. "
        f"Annual interest rate: {annual_rate:.3%}. "
        f"Loan term: {term_display}. "
        f"Monthly payment: ${monthly_payment:,.2f}. "
        f"Total amount paid: ${total_paid:,.2f}. "
        f"Total interest paid: ${total_interest:,.2f}. "
        f"Use the monthly payment figure (${monthly_payment:,.2f}) as 'proposed_loan_payment' in calculate_dti."
    )


def _tool_generate_qualification_decision(arguments: dict) -> str:
    missing = _require(arguments, "dti_ratio", "loan_type", "collateral", "loan_amount", "credit_score", "annual_income", "employment_years", "down_payment_percent")
    if missing:
        return f"ERROR: generate_qualification_decision is missing required fields: {', '.join(missing)}."

    errors = _collect_errors(
        _non_negative(arguments["dti_ratio"], "dti_ratio"),
        _positive(arguments["loan_amount"], "loan_amount"),
        _non_negative(arguments["credit_score"], "credit_score"),
        _positive(arguments["annual_income"], "annual_income"),
        _non_negative(arguments["employment_years"], "employment_years"),
        _non_negative(arguments["down_payment_percent"], "down_payment_percent"),
    )
    if errors:
        return "ERROR: generate_qualification_decision received invalid values — " + "; ".join(errors) + "."

    dti = float(arguments["dti_ratio"])
    loan_type = str(arguments["loan_type"]).strip()
    collateral = str(arguments["collateral"]).strip() or "none"
    amount = float(arguments["loan_amount"])
    score = float(arguments["credit_score"])
    income = float(arguments["annual_income"])
    years = float(arguments["employment_years"])
    down = float(arguments["down_payment_percent"])

    if not (300 <= score <= 850):
        return f"ERROR: generate_qualification_decision — credit_score {score} is outside the valid range (300–850)."

    # Qualification logic
    flags: list[str] = []
    positive_factors: list[str] = []

    if score < 580:
        flags.append(f"Credit score {score:.0f} is below the minimum threshold of 580.")
    elif score >= 700:
        positive_factors.append(f"Strong credit score ({score:.0f}).")

    if dti > 0.50:
        flags.append(f"DTI of {dti:.1%} exceeds the 50% maximum.")
    elif dti <= 0.36:
        positive_factors.append(f"Healthy DTI ({dti:.1%}).")

    if years < 1:
        flags.append("Employment history under 1 year is a risk factor.")
    elif years >= 2:
        positive_factors.append(f"Stable employment ({years:.1f} years).")

    if down >= 20:
        positive_factors.append(f"Strong down payment ({down:.1f}%).")
    elif 0 < down < 10:
        flags.append(f"Low down payment ({down:.1f}%) may require PMI or additional review.")

    qualified = score >= 580 and dti <= 0.50
    decision = "CONDITIONALLY APPROVED" if qualified else "FURTHER REVIEW NEEDED"

    flags_section = (" Concerns: " + " ".join(flags)) if flags else " No major disqualifying factors identified."
    positives_section = (" Strengths: " + " ".join(positive_factors)) if positive_factors else ""

    return (
        f"Qualification decision: {decision}. "
        f"Loan type: {loan_type}. "
        f"Requested amount: ${amount:,.0f}. "
        f"Credit score: {score:.0f}. "
        f"DTI: {dti:.1%}. "
        f"Annual income: ${income:,.0f}. "
        f"Employment: {years:.1f} years. "
        f"Collateral: {collateral}. "
        f"Down payment: {down:.1f}%."
        f"{flags_section}"
        f"{positives_section}"
    )


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_TOOL_HANDLERS = {
    "analyze_income": _tool_analyze_income,
    "analyze_bank_statements": _tool_analyze_bank_statements,
    "check_credit_profile": _tool_check_credit_profile,
    "calculate_dti": _tool_calculate_dti,
    "calculate_loan_terms": _tool_calculate_loan_terms,
    "generate_qualification_decision": _tool_generate_qualification_decision,
}


def execute_tool(name: str, arguments: dict) -> str:
    """Dispatch a tool call by name and return a result string.

    Always returns a string — never raises. Unknown tool names and
    unexpected exceptions are surfaced as ERROR strings so the agent
    can report them gracefully rather than crashing.
    """
    if not isinstance(arguments, dict):
        return f"ERROR: execute_tool — 'arguments' must be a dict, got {type(arguments).__name__}."

    handler = _TOOL_HANDLERS.get(name)
    if handler is None:
        known = ", ".join(sorted(_TOOL_HANDLERS))
        return f"ERROR: Unknown tool '{name}'. Known tools: {known}."

    try:
        return handler(arguments)
    except Exception as exc:  # noqa: BLE001
        return f"ERROR: Unexpected error in tool '{name}': {type(exc).__name__}: {exc}."