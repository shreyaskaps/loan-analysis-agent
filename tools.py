"""Tool definitions and implementations for the loan analysis agent."""

TOOL_DEFINITIONS = [
    {
        "name": "analyze_income",
        "description": (
            "Analyze and verify income documentation. Call this IMMEDIATELY when you see "
            "income data from pay stubs, W-2s, tax returns, or offer letters. "
            "Do NOT wait for additional documents — call once per employer/income source. "
            "For job changes, call SEPARATELY for each employer."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "employer": {"type": "string", "description": "Exact employer name from the document"},
                "income_type": {
                    "type": "string",
                    "description": "Income type exactly as described: W2, W-2, 1099, salary, self-employed, W-2 + 1099, SSA + pension, fixed, etc.",
                },
                "annual_income": {"type": "number", "description": "Annual gross income in dollars. If only monthly given, multiply by 12."},
                "monthly_gross": {"type": "number", "description": "Monthly gross income in dollars. If only annual given, divide by 12."},
                "years_employed": {"type": "number", "description": "Years at THIS specific employer (not total work history). Use 0.25 for 3 months, etc."},
                "additional_income": {"type": "number", "description": "Additional income (rental, freelance, etc). Use 0 if none mentioned."},
            },
            "required": ["employer", "income_type", "annual_income", "monthly_gross", "years_employed", "additional_income"],
        },
        "input_examples": [
            {
                "employer": "BrightLayer Tech",
                "income_type": "W-2 salary",
                "annual_income": 88500,
                "monthly_gross": 7375,
                "years_employed": 3,
                "additional_income": 0,
            },
            {
                "employer": "Sara Patel Consulting",
                "income_type": "self-employed",
                "annual_income": 64800,
                "monthly_gross": 5400,
                "years_employed": 4,
                "additional_income": 0,
            },
        ],
    },
    {
        "name": "analyze_bank_statements",
        "description": (
            "Analyze bank statements for cash flow, reserves, and deposit patterns. "
            "Call this IMMEDIATELY when you see bank statement data — do NOT ask for clarification. "
            "Extract all values from the document description."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "num_months": {"type": "number", "description": "Number of months of statements"},
                "overdrafts": {"type": "number", "description": "Number of overdrafts. Use 0 if none mentioned, use 1 if 'one overdraft' mentioned."},
                "large_deposits": {
                    "description": "Large/unusual deposits. Array of numbers like [8000, 3200] for multiple, single number for one, or 0 if none.",
                },
                "monthly_deposits": {"type": "number", "description": "Average monthly deposit amount"},
                "monthly_withdrawals": {"type": "number", "description": "Average monthly withdrawal amount"},
                "average_monthly_balance": {"type": "number", "description": "Average monthly account balance"},
            },
            "required": ["num_months", "overdrafts", "large_deposits", "monthly_deposits", "monthly_withdrawals", "average_monthly_balance"],
        },
        "input_examples": [
            {
                "num_months": 8,
                "overdrafts": 1,
                "large_deposits": 0,
                "monthly_deposits": 5200,
                "monthly_withdrawals": 3800,
                "average_monthly_balance": 6500,
            },
            {
                "num_months": 24,
                "overdrafts": 3,
                "large_deposits": [12000, 8000],
                "monthly_deposits": 5400,
                "monthly_withdrawals": 3150,
                "average_monthly_balance": 4200,
            },
        ],
    },
    {
        "name": "check_credit_profile",
        "description": (
            "Check borrower's credit profile. Call this as soon as you have credit_score AND open_accounts. "
            "Do NOT wait for credit_utilization or credit_history_years — those are optional. "
            "Only include optional fields if the user/document explicitly provided them."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "credit_score": {"type": "number", "description": "Credit score (FICO or equivalent)"},
                "open_accounts": {"type": "number", "description": "Total number of open credit accounts"},
                "derogatory_marks": {"description": "Number of derogatory marks, or 'none'. OMIT if not provided."},
                "credit_utilization": {"description": "Credit utilization as decimal (0.18) or percentage (18). OMIT if not provided."},
                "credit_history_years": {"type": "number", "description": "Years of credit history. OMIT if not provided."},
            },
            "required": ["credit_score", "open_accounts"],
        },
        "input_examples": [
            {
                "credit_score": 685,
                "open_accounts": 5,
            },
            {
                "credit_score": 720,
                "open_accounts": 6,
                "derogatory_marks": "none",
                "credit_utilization": 12,
                "credit_history_years": 8,
            },
        ],
    },
    {
        "name": "calculate_dti",
        "description": (
            "Calculate debt-to-income ratio. Call this when you have monthly debts, "
            "gross income, and proposed loan payment amounts."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "monthly_debts": {"type": "number", "description": "Total existing monthly debt payments (car, student loan, credit cards, etc.)"},
                "monthly_gross_income": {"type": "number", "description": "Monthly gross income"},
                "proposed_loan_payment": {"type": "number", "description": "Proposed monthly payment for the new loan"},
            },
            "required": ["monthly_debts", "monthly_gross_income", "proposed_loan_payment"],
        },
        "input_examples": [
            {
                "monthly_debts": 850,
                "monthly_gross_income": 7375,
                "proposed_loan_payment": 1200,
            },
        ],
    },
    {
        "name": "generate_qualification_decision",
        "description": (
            "Generate preliminary loan qualification decision. "
            "Call this IMMEDIATELY after calculate_dti, using all gathered data."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "dti_ratio": {"type": "number", "description": "Calculated DTI ratio as decimal (e.g. 0.35)"},
                "loan_type": {"type": "string", "description": "Loan type: personal_loan, auto_loan, HELOC, 30-year fixed, small_business, debt_consolidation, etc."},
                "collateral": {"type": "string", "description": "Collateral description or 'none'/'unsecured'"},
                "loan_amount": {"type": "number", "description": "Requested loan amount (original, before down payment)"},
                "credit_score": {"type": "number", "description": "Borrower's credit score"},
                "annual_income": {"type": "number", "description": "Borrower's annual income"},
                "employment_years": {"type": "number", "description": "Years of employment"},
                "down_payment_percent": {"type": "number", "description": "Down payment as percentage (0 if none)"},
            },
            "required": ["dti_ratio", "loan_type", "collateral", "loan_amount", "credit_score", "annual_income", "employment_years", "down_payment_percent"],
        },
        "input_examples": [
            {
                "dti_ratio": 0.247,
                "loan_type": "30-year fixed",
                "collateral": "residential property",
                "loan_amount": 350000,
                "credit_score": 720,
                "annual_income": 88500,
                "employment_years": 3,
                "down_payment_percent": 10,
            },
        ],
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
