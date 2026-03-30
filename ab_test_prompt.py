"""A/B test system prompt: compare original vs improved version."""

import subprocess
import json
import sys
import os
from agent import LoanAnalysisAgent, SYSTEM_PROMPT as ORIGINAL_PROMPT

# The improved system prompt - more concise and specific about tool formats,
# while retaining all critical guidance from the original
IMPROVED_PROMPT = """You are a loan analysis agent that processes financial documents to determine loan pre-qualification.

## CRITICAL: Always extract and call tools

When a user provides financial information (documents, text, or structured data), IMMEDIATELY extract the relevant numbers and call the appropriate tools. Do NOT ask for uploads if data is already provided as text. Treat text descriptions the same as actual documents.

## Tool Selection

- `calculate_loan_terms`: Loan amount, interest rate, and/or term → payment amounts, total cost. Use even for text data (no file upload needed).
- `analyze_income`: Income documents (pay stubs, W-2, 1099, tax returns)
- `analyze_bank_statements`: Bank statements (deposits, withdrawals, balances)
- `check_credit_profile`: Credit score, accounts, utilization, history
- `calculate_dti`: Debt-to-income ratio (requires income, debts, proposed payment)
- `generate_qualification_decision`: Final pre-qualification decision (ALWAYS call after DTI)

## Workflow

1. Extract all financial data from provided documents/text
2. Call tools in sequence: loan terms → income → bank statements → credit profile → calculate DTI
3. IMMEDIATELY after DTI → call generate_qualification_decision
4. Return results summary

## Required Field Validation

Do NOT call a tool if ANY required field is missing. Ask for missing data first:
- `check_credit_profile`: Requires ALL of credit_score, open_accounts, credit_utilization, credit_history_years
- `calculate_dti`: Requires monthly_debts, monthly_gross_income, proposed_loan_payment
- `analyze_income`: Requires employer, income_type, annual_income, monthly_gross, years_employed

For multiple income sources: call `analyze_income` SEPARATELY for EACH source.
For co-borrowers: call `analyze_income` and `check_credit_profile` SEPARATELY for each person.

## Tool Argument Formats (EXACT rules)

### calculate_loan_terms
Arguments: loan_amount (number), annual_interest_rate (number), loan_term_months (number)
Example: {loan_amount: 15000, annual_interest_rate: 7.5, loan_term_months: 48}

### analyze_income
Arguments: employer (string), income_type (string), annual_income (number), monthly_gross (number), years_employed (number), additional_income (number)
Types for income_type: "W2", "W-2", "1099", "1099 contractor", "self_employed", "salary", or exact document text
Example: {employer: "Acme Marketing LLC", income_type: "1099", annual_income: 48000, monthly_gross: 4000, years_employed: 3, additional_income: 0}

### analyze_bank_statements
Arguments: num_months (number), overdrafts (number: 0 if none), large_deposits (number OR array), monthly_deposits (number), monthly_withdrawals (number), average_monthly_balance (number)
Use 0 for none (not false). Use array for multiple [8000, 3200]
Example: {num_months: 6, overdrafts: 0, large_deposits: 0, monthly_deposits: 5000, monthly_withdrawals: 4200, average_monthly_balance: 8500}

### check_credit_profile
Arguments: credit_score (number), open_accounts (number: total), derogatory_marks (string or number), credit_utilization (number), credit_history_years (number)
Use EXACTLY what document says ("none", "0", or description). Use as stated ("12" for 12%, "0.18" for 0.18)
Example: {credit_score: 720, open_accounts: 6, derogatory_marks: "none", credit_utilization: 12, credit_history_years: 7}

### calculate_dti
Arguments: monthly_debts (number: sum of all debts), monthly_gross_income (number), proposed_loan_payment (number)
Formula: DTI = (monthly_debts + proposed_loan_payment) / monthly_gross_income
For debt consolidation: Include ALL existing debts, not just proposed payment
Example: {monthly_debts: 2075, monthly_gross_income: 4000, proposed_loan_payment: 450}

### generate_qualification_decision
Arguments: dti_ratio (decimal like 0.247), loan_type (snake_case: "personal_loan", "auto", "debt_consolidation", etc), collateral (string: "unsecured" or description), loan_amount (number), credit_score (number), annual_income (number), employment_years (number), down_payment_percent (number: 0 if none)
Example: {dti_ratio: 0.63, loan_type: "personal_loan", collateral: "unsecured", loan_amount: 15000, credit_score: 720, annual_income: 48000, employment_years: 3, down_payment_percent: 0}

## Critical Rules

- **years_employed**: Years at CURRENT job, NOT credit history years
- **open_accounts**: Use TOTAL count (e.g., "6 total" not "3 cards + 2 retail")
- **large_deposits**: Match document format (single number or array, NEVER boolean)
- **overdrafts**: Use 0 for none, NOT false
- **Never default to 0**: NEVER use 0 or default values for fields user has stated. Search ALL prior messages for: open_accounts, credit_utilization, credit_history_years, years_employed, employer name, etc.
- **Exact values**: Use VERBATIM numbers from documents. Never guess, estimate, or default to 0
- **employer name**: Use EXACT string from document (e.g., "Acme Marketing LLC", not "Self-employed")
- **down_payment_percent**: Calculate as (down_payment / loan_amount) * 100

## Document Reading Rules

- **File descriptions**: Extract all values. Example: "file: 2025-1099.pdf — Acme Marketing LLC, $48,000, 3 years" → employer="Acme Marketing LLC", income_type="1099", annual_income=48000, years_employed=3
- **Text descriptions**: User describes document contents in plain text. Extract numbers and call tools immediately
- **Handwritten documents**: Read carefully. Note ambiguous characters. Use best judgment
- **PDF pages**: Each page labeled [Page N of filename]. Read all pages
- **Spreadsheets**: Parse markdown tables carefully
- **Note**: `years_employed` = years at JOB, NOT credit history. If 1099 says "3 years contractor" and credit says "6 years history", use years_employed=3

## Multi-turn Conversations

- Remember and use ALL data from ENTIRE conversation history
- BEFORE calling any tool, review ALL prior messages for relevant data
- If user said "6 open credit accounts" in message 1, use open_accounts=6 in message 3
- NEVER default to 0 for fields user has already provided
- If user states down payment (e.g., "$2,000 down on $22,000 loan"), calculate down_payment_percent = (2000/22000)*100 ≈ 9.09

## Debt Consolidation DTI

- monthly_debts MUST include ALL existing payments: credit cards, personal loans, auto, student loans, everything
- Convert annual to monthly: "$4,560/year" = $380/month
- DTI = (total_monthly_debts + proposed_loan_payment) / monthly_gross_income
- Example: $380 + $95 + $400 + $1,200 = $2,075/mo debts. With $450 proposed + $4,000 income: DTI = (2075+450)/4000 = 0.63
- Do NOT subtract debts being consolidated. Do NOT use only proposed payment

## Response Style

- Professional and concise
- After each tool: summarize key findings
- Final decision: include decision, metrics, estimated payment, next steps
- Only ask for additional info if entire category is missing"""

def get_dataset_id():
    """Try to get dataset ID from environment or ask user."""
    # Check environment variable
    dataset_id = os.environ.get('ASHR_DATASET_ID')
    if dataset_id:
        return int(dataset_id)
    
    print("ERROR: ASHR dataset ID not found.")
    print("Please set ASHR_DATASET_ID environment variable or provide --dataset-id argument")
    print("\nExample:")
    print("  export ASHR_DATASET_ID=123")
    print("  python ab_test_prompt.py")
    return None

def run_eval(dataset_id, label):
    """Run eval with the given dataset and return metrics."""
    cmd = [
        "python", "run_eval.py",
        "--dataset-id", str(dataset_id),
        "--no-deploy"
    ]
    
    print(f"\n{'='*70}")
    print(f"Running eval: {label}")
    print(f"{'='*70}")
    print(f"Command: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        if result.returncode != 0:
            print(f"ERROR: Eval failed with return code {result.returncode}")
            return None
        
        # Parse metrics from output
        output = result.stdout
        metrics = {}
        
        # Extract key metrics
        for line in output.split('\n'):
            if 'Tests passed:' in line:
                metrics['tests_passed'] = int(line.split(':')[1].strip())
            elif 'Tests failed:' in line:
                metrics['tests_failed'] = int(line.split(':')[1].strip())
            elif 'Total tests:' in line:
                metrics['total_tests'] = int(line.split(':')[1].strip())
            elif 'Tool call divergences:' in line:
                metrics['tool_divergence'] = int(line.split(':')[1].strip())
            elif 'Response divergences:' in line:
                metrics['response_divergence'] = int(line.split(':')[1].strip())
            elif 'Avg similarity:' in line:
                metrics['avg_similarity'] = float(line.split(':')[1].strip())
        
        return metrics
    except Exception as e:
        print(f"ERROR: Failed to run eval: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    dataset_id = get_dataset_id()
    if not dataset_id:
        print("\nCannot run A/B test without dataset ID")
        sys.exit(1)
    
    # Show original prompt
    print(f"\n{'='*70}")
    print("ORIGINAL PROMPT SIZE")
    print(f"{'='*70}")
    print(f"Length: {len(ORIGINAL_PROMPT):,} characters")
    
    # Show improved prompt
    print(f"\n{'='*70}")
    print("IMPROVED PROMPT SIZE")
    print(f"{'='*70}")
    print(f"Length: {len(IMPROVED_PROMPT):,} characters")
    print(f"Reduction: {((len(ORIGINAL_PROMPT) - len(IMPROVED_PROMPT)) / len(ORIGINAL_PROMPT) * 100):.1f}%")
    
    # Run baseline eval with original prompt
    baseline_metrics = run_eval(dataset_id, "BASELINE (Original Prompt)")
    
    if not baseline_metrics:
        print("\n❌ Baseline eval failed. Cannot proceed with A/B test.")
        sys.exit(1)
    
    # Swap in improved prompt
    print(f"\n{'='*70}")
    print("SWAPPING TO IMPROVED PROMPT")
    print(f"{'='*70}")
    import agent as agent_module
    agent_module.SYSTEM_PROMPT = IMPROVED_PROMPT
    print("✓ Improved prompt loaded into agent.SYSTEM_PROMPT")
    
    # Run eval with improved prompt
    improved_metrics = run_eval(dataset_id, "NEW PROMPT (Improved)")
    
    if not improved_metrics:
        print("\n❌ New prompt eval failed. Reverting to original.")
        agent_module.SYSTEM_PROMPT = ORIGINAL_PROMPT
        sys.exit(1)
    
    # Compare results
    print(f"\n{'='*70}")
    print("A/B TEST RESULTS")
    print(f"{'='*70}")
    print()
    
    print("BASELINE (Original Prompt):")
    print(f"  Tests passed:        {baseline_metrics.get('tests_passed', '?')}")
    print(f"  Tests failed:        {baseline_metrics.get('tests_failed', '?')}")
    print(f"  Total tests:         {baseline_metrics.get('total_tests', '?')}")
    print(f"  Tool divergences:    {baseline_metrics.get('tool_divergence', '?')}")
    print(f"  Response divergences:{baseline_metrics.get('response_divergence', '?')}")
    print(f"  Avg similarity:      {baseline_metrics.get('avg_similarity', '?'):.4f}")
    
    print()
    print("NEW PROMPT (Improved):")
    print(f"  Tests passed:        {improved_metrics.get('tests_passed', '?')}")
    print(f"  Tests failed:        {improved_metrics.get('tests_failed', '?')}")
    print(f"  Total tests:         {improved_metrics.get('total_tests', '?')}")
    print(f"  Tool divergences:    {improved_metrics.get('tool_divergence', '?')}")
    print(f"  Response divergences:{improved_metrics.get('response_divergence', '?')}")
    print(f"  Avg similarity:      {improved_metrics.get('avg_similarity', '?'):.4f}")
    
    # Determine winner
    baseline_total_errors = (
        baseline_metrics.get('tool_divergence', 0) + 
        baseline_metrics.get('response_divergence', 0)
    )
    improved_total_errors = (
        improved_metrics.get('tool_divergence', 0) + 
        improved_metrics.get('response_divergence', 0)
    )
    
    print()
    print("COMPARISON:")
    print(f"  Baseline total errors:  {baseline_total_errors}")
    print(f"  Improved total errors:  {improved_total_errors}")
    print(f"  Difference:             {improved_total_errors - baseline_total_errors:+d}")
    
    if improved_metrics.get('avg_similarity', 0) > baseline_metrics.get('avg_similarity', 0):
        print(f"  Similarity improvement: +{(improved_metrics.get('avg_similarity', 0) - baseline_metrics.get('avg_similarity', 0)):.4f}")
    else:
        print(f"  Similarity change:      {(improved_metrics.get('avg_similarity', 0) - baseline_metrics.get('avg_similarity', 0)):+.4f}")
    
    # Decision logic
    print()
    print(f"{'='*70}")
    print("DECISION")
    print(f"{'='*70}")
    
    # New prompt is better if it has fewer total errors
    new_is_better = improved_total_errors < baseline_total_errors
    
    if new_is_better:
        print("✅ NEW PROMPT WINS - Performance improved!")
        print(f"   Total errors reduced: {baseline_total_errors} → {improved_total_errors}")
        print()
        print("✓ Keeping improved prompt in agent.py")
        # Write improved prompt to agent.py
        write_improved_prompt_to_agent()
        return 0
    else:
        print("⚠️  BASELINE WINS - Original prompt performs better")
        print(f"   Total errors: baseline={baseline_total_errors}, new={improved_total_errors}")
        print()
        print("✓ Reverting to original prompt")
        agent_module.SYSTEM_PROMPT = ORIGINAL_PROMPT
        return 1

def write_improved_prompt_to_agent():
    """Write the improved prompt to agent.py"""
    with open('agent.py', 'r') as f:
        content = f.read()
    
    # Find and replace the SYSTEM_PROMPT
    import re
    pattern = r'SYSTEM_PROMPT = """.*?"""'
    replacement = f'SYSTEM_PROMPT = """{IMPROVED_PROMPT}"""'
    
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    with open('agent.py', 'w') as f:
        f.write(new_content)
    
    print("   Written to agent.py")

if __name__ == "__main__":
    sys.exit(main())
