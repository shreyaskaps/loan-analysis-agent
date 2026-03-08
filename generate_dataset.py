"""Generate a comprehensive Ashr test dataset for the loan analysis agent.

Usage:
    source venv/bin/activate
    python generate_dataset.py
"""

import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from ashr_labs import AshrLabsClient
from tools import TOOL_DEFINITIONS
from agent import SYSTEM_PROMPT


def main():
    client = AshrLabsClient.from_env()
    info = client.init()
    print(f"Authenticated as {info['user']['id']}")

    # Build tool schemas for request_input_schema
    tool_schemas = []
    for tool in TOOL_DEFINITIONS:
        tool_schemas.append({
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["input_schema"],
        })

    request_input_schema = {
        "type": "object",
        "properties": {"agent": {"type": "object"}, "context": {"type": "object"}},
        "required": ["agent", "context"],
        "tools": tool_schemas,
    }

    gen_config = {
        "agent": {
            "name": "Loan Analysis Agent",
            "tools": TOOL_DEFINITIONS,
            "description": (
                "A loan pre-qualification agent that analyzes financial documents "
                "(PDFs, scanned/handwritten pages, images, spreadsheets) to determine "
                "whether an applicant qualifies for a loan. It extracts data from "
                "documents, analyzes income, bank statements, credit profiles, "
                "calculates DTI, and generates a qualification decision."
            ),
            "output_format": {"type": "text"},
            "system_prompt": (
                "You are a loan pre-qualification agent. You analyze financial documents "
                "(pay stubs, bank statements, credit reports, loan applications) and call "
                "tools in order: analyze_income, analyze_bank_statements, check_credit_profile, "
                "calculate_dti, then generate_qualification_decision. Extract exact values from "
                "documents. Handle co-borrowers separately. Flag missing or stale documents."
            ),
            "accepted_inputs": {"text": True, "audio": False, "file": True, "image": True, "video": False},
        },
        "context": {
            "domain": "financial services / lending",
            "use_case": "Loan pre-qualification from uploaded financial documents",
            "scenario_context": """This agent processes loan applications by analyzing financial documents that users upload.
The agent must handle a wide variety of real-world document scenarios:

DOCUMENT TYPES:
- Pay stubs and W-2 forms (digital PDF or scanned images)
- Bank statements (multi-page PDFs, sometimes handwritten ledgers)
- Credit reports (digital or scanned)
- Loan applications with applicant details
- Tax returns (1040, 1099 forms)
- Handwritten financial summaries from applicants
- Spreadsheets with financial data (CSV/Excel)
- Photos of physical documents (receipts, property deeds, vehicle titles)

LOAN TYPES TO TEST:
- Personal unsecured loans ($1,000–$50,000)
- Auto loans with vehicle collateral
- Home mortgages (30-year fixed, 15-year, ARM)
- HELOC (home equity line of credit)
- Small business / working capital loans
- Debt consolidation loans
- Student loan refinancing

APPLICANT PROFILES TO TEST:
- W-2 salaried employees with strong credit (easy case)
- Self-employed / 1099 contractors with variable income
- Retired applicants on Social Security + pension
- Co-borrower / joint applications (two applicants)
- Applicants with thin credit files (short history, few accounts)
- Applicants with derogatory marks or low scores
- High-income applicants with high existing debt (DTI edge case)
- First-time borrowers with no credit history
- Applicants consolidating existing debt

EDGE CASES:
- Documents with stale dates that need flagging
- Handwritten numbers that could be ambiguous (e.g., 1 vs 7)
- Income discrepancy between pay stub and application
- Missing documents (agent should ask for them)
- Very high DTI ratios (>50%) that should fail qualification
- Excellent profiles that should clearly pass
- Borderline cases near qualification thresholds
- Multiple large unexplained deposits in bank statements
- Applicant with overdraft history
- Documents with explicit key-value pairs (e.g., "monthly_gross = 4800")

WORKFLOW:
1. User provides documents (as text descriptions representing uploaded files)
2. Agent extracts financial data from each document
3. Agent calls analyze_income, analyze_bank_statements, check_credit_profile in sequence
4. Agent calls calculate_dti with extracted numbers
5. Agent MUST call generate_qualification_decision immediately after DTI
6. Agent provides final summary with decision, metrics, and next steps

CRITICAL BEHAVIORS TO TEST:
- Agent must call all 5 tools in the correct order for a complete application
- Agent must use exact values from documents (not approximations)
- Agent must chain calculate_dti → generate_qualification_decision without stopping
- Agent must handle co-borrowers by calling income/credit tools separately for each
- Agent must flag missing documents and ask for them
- DTI calculation: (monthly_debts + proposed_loan_payment) / monthly_gross_income""",
            "sample_data": {
                "example_pay_stub": {
                    "employer": "Acme Corp",
                    "income_type": "W-2",
                    "annual_income": 85000,
                    "monthly_gross": 7083,
                    "years_employed": 5,
                    "pay_period": "biweekly",
                },
                "example_bank_statement": {
                    "num_months": 3,
                    "average_monthly_balance": 12500,
                    "monthly_deposits": 7200,
                    "monthly_withdrawals": 6800,
                    "overdrafts": 0,
                    "large_deposits": 0,
                },
                "example_credit_report": {
                    "credit_score": 720,
                    "open_accounts": 5,
                    "derogatory_marks": "none",
                    "credit_utilization": 18,
                    "credit_history_years": 8,
                },
                "example_loan_application": {
                    "loan_type": "personal_loan",
                    "loan_amount": 25000,
                    "collateral": "none",
                    "monthly_debts": 850,
                    "proposed_payment": 450,
                    "down_payment_percent": 0,
                },
            },
            "user_persona": (
                "Loan applicants uploading their financial documents for pre-qualification. "
                "They may provide documents in various formats (PDF, scans, photos, spreadsheets). "
                "Some are sophisticated borrowers, others are first-time applicants who may "
                "not know which documents to provide."
            ),
        },
        "metadata": {
            "tags": ["lending", "loan-analysis", "document-processing", "financial", "multimodal"],
            "description": "Comprehensive test suite for multimodal loan analysis agent",
            "dataset_name": "Loan Analysis Agent - Comprehensive Eval v1",
        },
        "test_config": {
            "num_variations": 5,
            "coverage": {"happy_path": True, "edge_cases": True},
        },
        "generation_options": {
            "generate_audio": False,
            "generate_files": False,
            "generate_simulations": False,
        },
    }

    print("Submitting dataset generation request...")
    print("This may take several minutes...")

    dataset_id, source = client.generate_dataset(
        request_name="Loan Analysis Agent - Comprehensive Eval v1",
        config=gen_config,
        request_input_schema=request_input_schema,
        timeout=600,
        poll_interval=10,
    )

    num_scenarios = len(source.get("runs", {}))
    print(f"\nDataset generated! ID: {dataset_id}")
    print(f"Scenarios: {num_scenarios}")

    # Print scenario summaries
    for run_id, run_data in source.get("runs", {}).items():
        title = run_data.get("title", "Untitled")
        num_actions = len(run_data.get("actions", []))
        print(f"  - [{run_id}] {title} ({num_actions} actions)")

    print(f"\nTo run evaluation:")
    print(f"  python run_eval.py --dataset-id {dataset_id}")

    return dataset_id


if __name__ == "__main__":
    dataset_id = main()
