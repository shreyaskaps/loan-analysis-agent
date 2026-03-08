"""Run evaluation against an Ashr dataset, show results, and deploy.

Usage:
    # Using environment variable (recommended):
    export ASHR_LABS_API_KEY=tp_your_key_here
    python run_eval.py --dataset-id 333

    # Or with explicit key:
    python run_eval.py --dataset-id 333 --api-key tp_your_key_here

    # Skip deployment (inspect only):
    python run_eval.py --dataset-id 333 --no-deploy
"""

import argparse
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from ashr_labs import AshrLabsClient, EvalRunner
from agent import LoanAnalysisAgent
from comparators import custom_tool_comparator, custom_text_comparator


def main():
    parser = argparse.ArgumentParser(description="Run Ashr evaluation for loan analysis agent")
    parser.add_argument("--dataset-id", type=int, required=True, help="Ashr dataset ID to evaluate against")
    parser.add_argument("--api-key", type=str, default=None, help="Ashr API key (or set ASHR_LABS_API_KEY env var)")
    parser.add_argument("--no-deploy", action="store_true", help="Skip deploying results to Ashr")
    args = parser.parse_args()

    # Initialize client
    if args.api_key:
        client = AshrLabsClient(api_key=args.api_key)
    else:
        client = AshrLabsClient.from_env()

    info = client.init()
    runner_id = info["user"]["id"]
    print(f"Authenticated as runner_id={runner_id}")

    # Initialize agent
    agent = LoanAnalysisAgent()
    print(f"Loading dataset {args.dataset_id}...")

    # Create eval runner with custom comparators
    runner = EvalRunner.from_dataset(
        client,
        dataset_id=args.dataset_id,
        tool_comparator=custom_tool_comparator,
        text_comparator=custom_text_comparator,
    )

    scenario_count = [0]

    def on_scenario(run_id, scenario):
        scenario_count[0] += 1
        print(f"\n[{scenario_count[0]}] Running scenario: {run_id}")

    print("Running evaluation...")
    run_builder = runner.run(agent, on_scenario=on_scenario)

    # Inspect results before deploying
    result = run_builder.build()
    metrics = result["aggregate_metrics"]

    print("\n" + "=" * 60)
    print("EVALUATION RESULTS")
    print("=" * 60)
    print(f"Total tests: {metrics['total_tests']}")
    print(f"Tests passed: {metrics['tests_passed']}")
    print(f"Tests failed: {metrics['tests_failed']}")
    print(f"Tool call divergences: {metrics['total_tool_call_divergence']}")
    print(f"Response divergences: {metrics['total_response_divergence']}")
    print(f"Avg similarity: {metrics['average_similarity_score']}")

    # Show per-test details for failures/divergences
    for test in result["tests"]:
        test_id = test["test_id"]
        errors = []
        for action in test.get("action_results", []):
            if action.get("action_type") == "tool_call":
                for tc in action.get("tool_calls", []):
                    status = tc.get("match_status", "")
                    if status != "exact":
                        exp = tc.get("expected", {})
                        act = tc.get("actual", {})
                        errors.append(
                            f"  TOOL [{status}] expected={exp.get('name')}({json.dumps(exp.get('arguments', {}), default=str)[:150]}) "
                            f"actual={act.get('name')}({json.dumps(act.get('arguments', {}), default=str)[:150]})"
                        )
                        if tc.get("divergence_notes"):
                            errors.append(f"    notes: {tc['divergence_notes'][:200]}")
            elif action.get("action_type") == "text" and action.get("actor") == "agent":
                status = action.get("match_status", "")
                if status == "divergent":
                    sim = action.get("semantic_similarity", 0)
                    errors.append(f"  TEXT [{status}] sim={sim:.2f}")

        if errors:
            print(f"\n--- {test_id} ---")
            for e in errors:
                print(e)

    # Deploy unless skipped
    if not args.no_deploy:
        print("\nDeploying results...")
        run_builder.deploy(client, dataset_id=args.dataset_id, runner_id=runner_id)
        print("Deployed!")
    else:
        print("\nSkipping deployment (--no-deploy).")

    # Return error count
    error_count = metrics["total_tool_call_divergence"] + metrics["total_response_divergence"]
    print(f"\nTotal errors: {error_count}")
    return error_count


if __name__ == "__main__":
    errors = main()
    sys.exit(0 if errors == 0 else 1)
