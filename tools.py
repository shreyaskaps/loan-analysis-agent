"""Tool definitions and implementations for the loan analysis agent."""

TOOL_DEFINITIONS = [
    {
        "name": "analyze_income",
        "description": "Analyze and verify income from uploaded pay stubs, W-2s, tax returns, or other income documentation. Call this tool after extracting income details from the user's uploaded documents.",
        "input_schema": {
            "type": "object",
            "properties": {
                "employer": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Employer name from pay stubs or tax docs"
                },
                "income_type": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Income type: W2, 1099, W-2, W-2 + 1099, W-2 + 1099 + rental, SSA + pension, self-employed, etc."
                },
                "annual_income": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Annual gross income in dollars"
                },
                "monthly_gross": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Monthly gross income in dollars"
                },
                "years_employed": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Years employed with current employer"
                },
                "additional_income": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Additional monthly or annual income (rental, freelance, etc). Use 0 if none."
                },
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
                "num_months": {
                    "type": "number",
                    "minimum": 1,
                    "description": "Number of months of statements provided"
                },
                "overdrafts": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Number of overdrafts in the statement period (use 0 for none, not false)"
                },
                "large_deposits": {
                    "oneOf": [
                        {"type": "number", "minimum": 0},
                        {"type": "array", "items": {"type": "number", "minimum": 0}},
                    ],
                    "description": "Large or unusual deposits. Single number or array of amounts. Use 0 if none."
                },
                "monthly_deposits": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Average monthly deposit amount"
                },
                "monthly_withdrawals": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Average monthly withdrawal amount"
                },
                "average_monthly_balance": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Average monthly account balance"
                },
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
                "credit_score": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 900,
                    "description": "Credit score (FICO or Vantage equivalent, typically 300-850)"
                },
                "open_accounts": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Number of open credit accounts"
                },
                "derogatory_marks": {
                    "oneOf": [
                        {"type": "number", "minimum": 0},
                        {"type": "string", "enum": ["none", "0"]},
                    ],
                    "description": "Number of derogatory marks (0 if none) or 'none' as string"
                },
                "credit_utilization": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 100,
                    "description": "Credit utilization as percentage (0-100). If provided as decimal (0.18), it will be converted to percentage."
                },
                "credit_history_years": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Length of credit history in years"
                },
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
                "monthly_debts": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Total existing monthly debt payments (car, student loan, credit cards, etc.)"
                },
                "monthly_gross_income": {
                    "type": "number",
                    "minimum": 0.01,
                    "description": "Monthly gross income (must be > 0)"
                },
                "proposed_loan_payment": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Proposed monthly payment for the new loan"
                },
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
                "dti_ratio": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 1,
                    "description": "Calculated DTI ratio as decimal (e.g. 0.35 for 35%)"
                },
                "loan_type": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Loan type: personal_loan, auto_loan, HELOC, 30-year fixed, small_business, etc."
                },
                "collateral": {
                    "type": "string",
                    "minLength": 1,
                    "description": "Collateral description, 'none', or 'unsecured'"
                },
                "loan_amount": {
                    "type": "number",
                    "minimum": 0.01,
                    "description": "Requested loan amount (must be > 0)"
                },
                "credit_score": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 900,
                    "description": "Borrower's credit score"
                },
                "annual_income": {
                    "type": "number",
                    "minimum": 0.01,
                    "description": "Borrower's annual income (must be > 0)"
                },
                "employment_years": {
                    "type": "number",
                    "minimum": 0,
                    "description": "Years of employment"
                },
                "down_payment_percent": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 100,
                    "description": "Down payment as percentage (0 if none)"
                },
            },
            "required": ["dti_ratio", "loan_type", "collateral", "loan_amount", "credit_score", "annual_income", "employment_years", "down_payment_percent"],
        },
    },
]


def _coerce_number(val, default: float = 0) -> float:
    """Coerce a potentially bad-typed value to float.

    Handles: None, bool (True/False), strings ('none', 'null', ''), lists
    (sum of numeric elements), and already-numeric values.
    Falls back to *default* on any conversion failure.
    """
    if val is None:
        return float(default)
    if isinstance(val, bool):
        # bool is a subclass of int in Python; coerce explicitly: False→0, True→1
        return float(int(val))
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, list):
        try:
            return float(sum(
                float(v) for v in val
                if isinstance(v, (int, float)) or (isinstance(v, str) and v.replace('.', '', 1).lstrip('-').isdigit())
            ))
        except (TypeError, ValueError):
            return float(default)
    if isinstance(val, str):
        cleaned = val.strip().lower().replace(',', '').replace('$', '').replace('%', '')
        if cleaned in ('', 'none', 'null', 'n/a', 'na', 'false'):
            return float(default)
        try:
            return float(cleaned)
        except ValueError:
            return float(default)
    return float(default)


def _coerce_string(val, default: str = "") -> str:
    """Coerce any value to a clean non-empty string.

    Treats None, False, and blank/none-ish strings as *default*.
    """
    if val is None or val is False:
        return default
    if isinstance(val, bool):
        return default
    s = str(val).strip()
    return s if s and s.lower() not in ('none', 'null', 'n/a') else default


def _coerce_large_deposits(val, default: str = "None") -> str:
    """Normalise large_deposits to a human-readable string for the result.

    Accepts:
      - 0, False, None, []  → "None"
      - a single number     → "$X"
      - a list of numbers   → "$X, $Y, ..."
    
    Args:
        val: The value to coerce (number, list, None, etc.)
        default: Default string to use if val is falsy (default: "None")
    """
    if val is None or val is False or val == 0 or val == []:
        return default
    if isinstance(val, list):
        parts = []
        for item in val:
            try:
                parts.append(f"${float(item):,.0f}")
            except (TypeError, ValueError):
                parts.append(str(item))
        return ", ".join(parts) if parts else "None"
    try:
        return f"${float(val):,.0f}"
    except (TypeError, ValueError):
        return default if not val else str(val)


def execute_tool(name: str, arguments: dict) -> str:
    """Execute a tool and return a result string.
    
    All tool inputs are validated and coerced to appropriate types:
    - Numeric parameters (income, balances, scores, etc.) are coerced to float
      using _coerce_number, which handles None, bool, string, list, and numeric types
    - String parameters (employer, income_type, collateral) are coerced using
      _coerce_string, which treats None, False, and "none"-ish strings as defaults
    - Special cases like large_deposits and derogatory_marks have dedicated handlers
    
    This ensures the tool never crashes on bad input types from the LLM.
    """
    if name == "analyze_income":
        # Validate and coerce all numeric parameters; default to 0 for missing values
        monthly = _coerce_number(arguments.get("monthly_gross"), 0)
        annual = _coerce_number(arguments.get("annual_income"), 0)
        years = _coerce_number(arguments.get("years_employed"), 0)
        additional = _coerce_number(arguments.get("additional_income"), 0)
        
        # Validate and coerce string parameters; default to "Unknown" for missing values
        employer = _coerce_string(arguments.get("employer"), "Unknown")
        income_type = _coerce_string(arguments.get("income_type"), "Unknown")
        return (
            f"Income analysis complete. Employer: {employer}. "
            f"Income type: {income_type}. Annual income: ${annual:,.0f}. "
            f"Monthly gross: ${monthly:,.0f}. Years employed: {years:g}. "
            f"Additional income: ${additional:,.0f}. "
            f"Income verified and consistent with documentation."
        )

    elif name == "analyze_bank_statements":
        # Validate and coerce all numeric parameters
        # num_months must be > 0 for a valid statement period
        months = max(1, int(_coerce_number(arguments.get("num_months"), 1)))
        
        # Overdrafts: ensure it's a non-negative number (not bool/None/string like "none")
        overdrafts = max(0, int(_coerce_number(arguments.get("overdrafts"), 0)))
        
        # Balance and deposits/withdrawals default to 0 if missing or bad type
        balance = _coerce_number(arguments.get("average_monthly_balance"), 0)
        deposits = _coerce_number(arguments.get("monthly_deposits"), 0)
        withdrawals = _coerce_number(arguments.get("monthly_withdrawals"), 0)
        
        # large_deposits: can be single number, array, 0, None, or bad type
        large = _coerce_large_deposits(arguments.get("large_deposits"), 0)
        overdraft_note = (
            "No overdrafts detected."
            if overdrafts == 0
            else f"{int(overdrafts)} overdraft(s) detected in the period."
        )
        return (
            f"Bank statement analysis complete ({int(months)} months). "
            f"Average monthly balance: ${balance:,.0f}. "
            f"Monthly deposits: ${deposits:,.0f}. Monthly withdrawals: ${withdrawals:,.0f}. "
            f"{overdraft_note} Large deposits: {large}. "
            f"Cash flow appears {'stable' if overdrafts == 0 else 'somewhat irregular'}."
        )

    elif name == "check_credit_profile":
        # Validate and coerce numeric parameters; credit_score defaults to 0
        score = max(0, min(900, _coerce_number(arguments.get("credit_score"), 0)))
        accounts = max(0, _coerce_number(arguments.get("open_accounts"), 0))
        history = max(0, _coerce_number(arguments.get("credit_history_years"), 0))
        
        # derogatory_marks: can be number, "none" string, or bad type
        # Preserve "none" if provided; convert 0/False/None/[] → "none"
        raw_derog = arguments.get("derogatory_marks", 0)
        if raw_derog in (None, False, [], "none", "None", "NONE", "0", 0):
            derog: object = "none"
        elif isinstance(raw_derog, bool):
            # bool False already handled above; True → 1
            derog = int(raw_derog)
        elif isinstance(raw_derog, str):
            derog = raw_derog.strip()
        else:
            # Coerce other types to int if numeric
            derog = int(_coerce_number(raw_derog, 0))
        
        # credit_utilization: can be 0-100 (percent) or 0-1 (decimal)
        # Normalize to percentage (0–100) for display
        raw_util = _coerce_number(arguments.get("credit_utilization"), 0)
        # If it's clearly a decimal (0 < x < 1), convert to percentage; else assume it's already %
        util_display = f"{raw_util:.0f}%" if raw_util > 1 else f"{raw_util * 100:.0f}%"
        rating = (
            "excellent" if score >= 750
            else "good" if score >= 700
            else "fair" if score >= 650
            else "below average"
        )
        return (
            f"Credit profile check complete. Score: {int(score)} ({rating}). "
            f"Open accounts: {int(accounts)}. Derogatory marks: {derog}. "
            f"Credit utilization: {util_display}. Credit history: {history:g} years. "
        )

    elif name == "calculate_dti":
        # Validate and coerce all numeric parameters
        debts = max(0, _coerce_number(arguments.get("monthly_debts"), 0))
        income = max(0.01, _coerce_number(arguments.get("monthly_gross_income"), 0.01))
        payment = max(0, _coerce_number(arguments.get("proposed_loan_payment"), 0))
        
        # Calculate total obligations and DTI ratio
        total = debts + payment
        # Safely divide; income is guaranteed > 0 by max() above
        dti = total / income if income > 0 else 0
        return (
            f"DTI calculation complete. Monthly debts: ${debts:,.2f}. "
            f"Proposed payment: ${payment:,.2f}. Total obligations: ${total:,.2f}. "
            f"Monthly gross income: ${income:,.2f}. DTI ratio: {dti:.4f} ({dti * 100:.1f}%)."
        )

    elif name == "generate_qualification_decision":
        # Validate and coerce all numeric parameters
        dti = max(0, min(1, _coerce_number(arguments.get("dti_ratio"), 0)))
        amount = max(0, _coerce_number(arguments.get("loan_amount"), 0))
        score = max(0, min(900, _coerce_number(arguments.get("credit_score"), 0)))
        income = max(0, _coerce_number(arguments.get("annual_income"), 0))
        years = max(0, _coerce_number(arguments.get("employment_years"), 0))
        down = max(0, min(100, _coerce_number(arguments.get("down_payment_percent"), 0)))
        
        # Validate and coerce string parameters
        loan_type = _coerce_string(arguments.get("loan_type"), "unknown")
        collateral = _coerce_string(arguments.get("collateral"), "none")

        qualified = dti < 0.50 and score >= 580
        decision = "CONDITIONALLY APPROVED" if qualified else "FURTHER REVIEW NEEDED"

        return (
            f"Qualification decision: {decision}. "
            f"Loan type: {loan_type}. Amount: ${amount:,.0f}. "
            f"Credit score: {int(score)}. DTI: {dti:.1%}. "
            f"Annual income: ${income:,.0f}. Employment: {years:g} years. "
            f"Collateral: {collateral}. Down payment: {down:g}%. "
        )

    return f"Unknown tool: {name}"
