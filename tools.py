"""Tool definitions and implementations for the loan analysis agent."""

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "calculate_loan_terms",
            "description": "Calculate loan payment amounts and total cost based on loan amount, interest rate, and term. Call this when the user provides loan parameters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "loan_amount": {"type": "number", "description": "Loan amount in dollars"},
                    "annual_interest_rate": {"type": "number", "description": "Annual interest rate as percentage (e.g., 7 for 7%)"},
                    "loan_term_months": {"type": "number", "description": "Loan term in months"},
                },
                "required": ["loan_amount", "annual_interest_rate", "loan_term_months"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_income",
            "description": "Analyze and verify income from uploaded pay stubs, W-2s, tax returns, or other income documentation. Call this tool after extracting income details from the user's uploaded documents.",
            "parameters": {
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
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_bank_statements",
            "description": "Analyze bank statements for cash flow health, reserves, overdrafts, and deposit patterns. Call this after extracting bank statement details from user uploads.",
            "parameters": {
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
    },
    {
        "type": "function",
        "function": {
            "name": "check_credit_profile",
            "description": "Check and evaluate a credit report. Call this after extracting credit report details from user uploads.",
            "parameters": {
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
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_dti",
            "description": "Calculate debt-to-income ratio. Call this with the borrower's monthly debts, gross income, and proposed new loan payment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "monthly_debts": {"type": "number", "description": "Total existing monthly debt payments (car, student loan, credit cards, etc.)"},
                    "monthly_gross_income": {"type": "number", "description": "Monthly gross income"},
                    "proposed_loan_payment": {"type": "number", "description": "Proposed monthly payment for the new loan"},
                },
                "required": ["monthly_debts", "monthly_gross_income", "proposed_loan_payment"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_qualification_decision",
            "description": "Generate a preliminary loan qualification decision based on all gathered data. Call this after income analysis, bank analysis, credit check, and DTI calculation are complete.",
            "parameters": {
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
    },
]


def execute_tool(name: str, arguments: dict) -> str:
    """Execute a tool and return a result string."""
    if name == "calculate_loan_terms":
        loan_amount = arguments.get("loan_amount", 0)
        annual_rate = arguments.get("annual_interest_rate", 0)
        term_months = arguments.get("loan_term_months", 0)
        
        if loan_amount <= 0 or term_months <= 0 or annual_rate < 0:
            return f"Invalid loan parameters. Loan amount: ${loan_amount}, Rate: {annual_rate}%, Term: {term_months} months."
        
        # Calculate monthly payment using standard amortization formula
        monthly_rate = annual_rate / 100 / 12
        if monthly_rate == 0:
            monthly_payment = loan_amount / term_months
        else:
            monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate) ** term_months) / ((1 + monthly_rate) ** term_months - 1)
        
        total_paid = monthly_payment * term_months
        total_interest = total_paid - loan_amount
        
        return (
            f"Loan calculation complete. Loan amount: ${loan_amount:,.2f}. "
            f"Interest rate: {annual_rate}%. Loan term: {term_months} months. "
            f"Monthly payment: ${monthly_payment:,.2f}. "
            f"Total interest: ${total_interest:,.2f}. Total paid: ${total_paid:,.2f}."
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
