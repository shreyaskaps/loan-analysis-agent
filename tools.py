"""Tool definitions and implementations for the loan analysis agent."""

TOOL_DEFINITIONS = [
    {
        "name": "calculate_loan_terms",
        "description": (
            "Calculate monthly payment, total interest, and full loan cost for a given loan. "
            "Call this when the user provides a loan amount, interest rate, and/or loan term and "
            "wants to know the payment structure. Do NOT require a file upload — plain-text input "
            "is sufficient. Do NOT substitute analyze_income or calculate_dti for this tool."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "loan_amount": {
                    "type": "number",
                    "description": (
                        "Principal loan amount in dollars (positive number). "
                        "Example: 15000 for a $15,000 loan."
                    ),
                },
                "annual_interest_rate": {
                    "type": "number",
                    "description": (
                        "Annual interest rate as a percentage (not a decimal). "
                        "Example: 7.5 for 7.5% APR. Valid range: 0–100."
                    ),
                },
                "loan_term_months": {
                    "type": "number",
                    "description": (
                        "Loan repayment term in months (positive integer). "
                        "Example: 48 for a 4-year loan, 360 for a 30-year mortgage."
                    ),
                },
            },
            "required": ["loan_amount", "annual_interest_rate", "loan_term_months"],
        },
    },
    {
        "name": "analyze_income",
        "description": (
            "Analyze and verify income from pay stubs, W-2s, 1099s, tax returns, or other income "
            "documentation. Call this ONLY for income documents — NOT for loan term or DTI calculations. "
            "Call separately for each income source or co-borrower."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "employer": {
                    "type": "string",
                    "description": (
                        "Exact employer or organization name as stated in the document. "
                        "Examples: 'Acme Marketing LLC', 'Riverdale School District', 'N/A (retired)'. "
                        "Do NOT substitute generic labels like 'Self-employed' unless the document says so."
                    ),
                },
                "income_type": {
                    "type": "string",
                    "description": (
                        "Income classification exactly as stated in the document. "
                        "Example values: 'W-2', 'W2', '1099', '1099 contractor', 'self_employed', "
                        "'W-2 + 1099', 'W-2 + 1099 + rental', 'SSA + pension', 'fixed', 'salary'. "
                        "Copy the exact string — do not paraphrase."
                    ),
                },
                "annual_income": {
                    "type": "number",
                    "description": (
                        "Annual gross income in dollars, taken verbatim from the document. "
                        "Example: 85000 for $85,000/year. "
                        "If only a pay-period amount is given, convert: biweekly × 26, weekly × 52, monthly × 12."
                    ),
                },
                "monthly_gross": {
                    "type": "number",
                    "description": (
                        "Monthly gross income in dollars. "
                        "Example: 7083.33 for $85,000/year ÷ 12. "
                        "If the document states monthly gross explicitly, use that exact figure."
                    ),
                },
                "years_employed": {
                    "type": "number",
                    "description": (
                        "Years at THIS specific employer/position, not total career length or credit history years. "
                        "Example: 3 if the document says '3 years as contractor for Acme'. "
                        "Validation: must be ≥ 0."
                    ),
                },
                "additional_income": {
                    "type": "number",
                    "description": (
                        "Additional monthly or annual income beyond primary income (rental, freelance, alimony, etc.). "
                        "Use 0 if none — never omit this field. "
                        "Example: 500 for $500/month side income."
                    ),
                },
            },
            "required": ["employer", "income_type", "annual_income", "monthly_gross", "years_employed", "additional_income"],
        },
    },
    {
        "name": "analyze_bank_statements",
        "description": (
            "Analyze bank statements for cash flow health, reserves, overdrafts, and deposit patterns. "
            "Call this after extracting bank statement details from user uploads."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "num_months": {
                    "type": "number",
                    "description": (
                        "Number of statement months provided (positive integer). "
                        "Example: 3 for three months of statements."
                    ),
                },
                "overdrafts": {
                    "type": "number",
                    "description": (
                        "Count of overdraft occurrences in the statement period. "
                        "Use 0 (integer) if no overdrafts — do NOT use false or null. "
                        "Example: 2 for two overdraft events."
                    ),
                },
                "large_deposits": {
                    "description": (
                        "Large or unusual deposits. "
                        "Example: use a single number for one deposit (8000), "
                        "an array for multiple ([8000, 3200]), "
                        "or 0 if none. "
                        "Validation: must match exactly what the document states — do not aggregate."
                    ),
                },
                "monthly_deposits": {
                    "type": "number",
                    "description": (
                        "Average monthly deposit total in dollars. "
                        "Example: 7200 for $7,200 average monthly deposits."
                    ),
                },
                "monthly_withdrawals": {
                    "type": "number",
                    "description": (
                        "Average monthly withdrawal total in dollars. "
                        "Example: 6800 for $6,800 average monthly withdrawals."
                    ),
                },
                "average_monthly_balance": {
                    "type": "number",
                    "description": (
                        "Average end-of-month account balance in dollars. "
                        "Example: 12500 for an average balance of $12,500."
                    ),
                },
            },
            "required": ["num_months", "overdrafts", "large_deposits", "monthly_deposits", "monthly_withdrawals", "average_monthly_balance"],
        },
    },
    {
        "name": "check_credit_profile",
        "description": (
            "Evaluate a credit report. Call this after extracting credit details from user uploads. "
            "Do NOT call until you have real values for ALL required fields. "
            "If any field is missing, ask the user before calling."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "credit_score": {
                    "type": "number",
                    "description": (
                        "FICO or VantageScore credit score as an integer. "
                        "Example: 720. Valid range: 300–850."
                    ),
                },
                "open_accounts": {
                    "type": "number",
                    "description": (
                        "Total number of open credit accounts (all types combined). "
                        "Example: 6 if the user says '6 open credit accounts (3 cards, 2 retail, 1 auto)' — use 6, not subcounts. "
                        "Validation: must be ≥ 0."
                    ),
                },
                "derogatory_marks": {
                    "description": (
                        "Derogatory mark count or description, copied exactly from the document. "
                        "Use the string 'none' if the document says none, 0 if the document says 0, "
                        "or the exact description. "
                        "Example: 'none', 0, or '1 collection account'. "
                        "Do NOT normalize or paraphrase."
                    ),
                },
                "credit_utilization": {
                    "description": (
                        "Credit utilization ratio, exactly as stated in the document. "
                        "If the document says '12%', use 12. If it says '0.12', use 0.12. "
                        "The comparator handles percent-vs-decimal normalization. "
                        "Validation: must be ≥ 0."
                    ),
                },
                "credit_history_years": {
                    "type": "number",
                    "description": (
                        "Length of credit history in years. "
                        "This is NOT the same as years_employed. "
                        "Example: 8 for 8 years of credit history. "
                        "Validation: must be ≥ 0."
                    ),
                },
            },
            "required": ["credit_score", "open_accounts", "derogatory_marks", "credit_utilization", "credit_history_years"],
        },
    },
    {
        "name": "calculate_dti",
        "description": (
            "Calculate the debt-to-income (DTI) ratio. "
            "Formula: DTI = (monthly_debts + proposed_loan_payment) / monthly_gross_income. "
            "Call this ONLY after you know exact monthly debts, income, and proposed payment. "
            "ALWAYS call generate_qualification_decision immediately after this tool — never stop at DTI."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "monthly_debts": {
                    "type": "number",
                    "description": (
                        "Sum of ALL existing monthly debt obligations in dollars "
                        "(car payments, student loans, credit card minimums, personal loans, etc.). "
                        "Do NOT include the proposed new loan payment here — that goes in proposed_loan_payment. "
                        "For debt consolidation: include ALL debts being paid off. "
                        "Convert annual figures to monthly (e.g., $4,560/yr ÷ 12 = $380/mo). "
                        "Example: 850 if the borrower has $850/month in existing obligations."
                    ),
                },
                "monthly_gross_income": {
                    "type": "number",
                    "description": (
                        "Borrower's monthly gross income in dollars (before taxes/deductions). "
                        "For co-borrowers, use combined household monthly gross. "
                        "Example: 7083 for $85,000/year ÷ 12."
                    ),
                },
                "proposed_loan_payment": {
                    "type": "number",
                    "description": (
                        "Estimated monthly payment for the NEW loan being applied for. "
                        "Use the result from calculate_loan_terms if available, or a reasonable estimate. "
                        "Example: 450 for a $450/month proposed payment. "
                        "Validation: must be > 0."
                    ),
                },
            },
            "required": ["monthly_debts", "monthly_gross_income", "proposed_loan_payment"],
        },
    },
    {
        "name": "generate_qualification_decision",
        "description": (
            "Generate a preliminary loan qualification decision. "
            "Call this IMMEDIATELY after calculate_dti — never skip this step. "
            "All prior analysis (income, bank, credit, DTI) should be complete before calling."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "dti_ratio": {
                    "type": "number",
                    "description": (
                        "Calculated DTI as a decimal (NOT a percentage). "
                        "Example: 0.35 for a 35% DTI. "
                        "Use the precise value from calculate_dti — do not round aggressively. "
                        "Validation: must be ≥ 0."
                    ),
                },
                "loan_type": {
                    "type": "string",
                    "description": (
                        "Loan type in snake_case or standard format matching the application. "
                        "Examples: 'personal_loan', 'auto', 'HELOC', '30-year fixed', "
                        "'debt_consolidation', 'working_capital', 'student_refinance'."
                    ),
                },
                "collateral": {
                    "type": "string",
                    "description": (
                        "Collateral description. Use 'unsecured' or 'none' for unsecured loans. "
                        "For secured loans, describe the collateral. "
                        "Examples: 'unsecured', 'none', 'vehicle', '123 Main St property'."
                    ),
                },
                "loan_amount": {
                    "type": "number",
                    "description": (
                        "The ORIGINAL requested loan amount in dollars (before any down payment). "
                        "Example: 22000 for a $22,000 loan even if the borrower puts $2,000 down."
                    ),
                },
                "credit_score": {
                    "type": "number",
                    "description": (
                        "Borrower's credit score from check_credit_profile. "
                        "For co-borrower applications, use the primary borrower's score unless specified otherwise. "
                        "Example: 720."
                    ),
                },
                "annual_income": {
                    "type": "number",
                    "description": (
                        "Borrower's annual gross income in dollars from analyze_income. "
                        "Example: 85000."
                    ),
                },
                "employment_years": {
                    "type": "number",
                    "description": (
                        "Years of employment from analyze_income (years at current employer). "
                        "Example: 5."
                    ),
                },
                "down_payment_percent": {
                    "type": "number",
                    "description": (
                        "Down payment as a percentage of the loan amount. Use 0 if none. "
                        "Formula: (down_payment_amount / loan_amount) * 100. "
                        "Example: 9.09 if the borrower puts $2,000 down on a $22,000 loan."
                    ),
                },
            },
            "required": ["dti_ratio", "loan_type", "collateral", "loan_amount", "credit_score", "annual_income", "employment_years", "down_payment_percent"],
        },
    },
]


def execute_tool(name: str, arguments: dict) -> str:
    """Execute a tool and return a result string."""
    if name == "calculate_loan_terms":
        principal = arguments.get("loan_amount", 0)
        annual_rate = arguments.get("annual_interest_rate", 0)
        term_months = arguments.get("loan_term_months", 0)
        monthly_rate = annual_rate / 100 / 12
        if monthly_rate > 0 and term_months > 0:
            monthly_payment = principal * (monthly_rate * (1 + monthly_rate) ** term_months) / ((1 + monthly_rate) ** term_months - 1)
        elif term_months > 0:
            monthly_payment = principal / term_months
        else:
            monthly_payment = 0
        total_paid = monthly_payment * term_months
        total_interest = total_paid - principal
        return (
            f"Loan terms calculated. Principal: ${principal:,.2f}. "
            f"Annual rate: {annual_rate}%. Term: {term_months} months. "
            f"Monthly payment: ${monthly_payment:,.2f}. "
            f"Total paid: ${total_paid:,.2f}. Total interest: ${total_interest:,.2f}."
        )

    elif name == "analyze_income":
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
