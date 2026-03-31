"""Test to validate the SYSTEM_PROMPT fix using reward model scoring."""

from agent import LoanAnalysisAgent, SYSTEM_PROMPT

def test_system_prompt_clean():
    """Verify the SYSTEM_PROMPT doesn't contain debugging notes."""
    debug_strings = [
        "Looking at the failure pattern",
        "calculate_loan_terms is never being called",
        "The fix needs to",
        "The most appropriate place is",
    ]
    
    for debug_str in debug_strings:
        assert debug_str not in SYSTEM_PROMPT, f"Found debug string in prompt: {debug_str}"
    
    # Verify it starts correctly
    assert SYSTEM_PROMPT.startswith("You are a loan analysis agent"), \
        "Prompt should start with 'You are a loan analysis agent'"
    
    print("✓ SYSTEM_PROMPT is clean and properly formatted")

def test_agent_instantiation():
    """Verify agent can be instantiated without errors."""
    agent = LoanAnalysisAgent()
    assert agent is not None
    assert agent.messages == []
    print("✓ Agent instantiates correctly")

def test_agent_reset():
    """Verify agent reset works."""
    agent = LoanAnalysisAgent()
    agent.messages.append({"test": "message"})
    agent.reset()
    assert agent.messages == []
    print("✓ Agent reset works correctly")

if __name__ == "__main__":
    test_system_prompt_clean()
    test_agent_instantiation()
    test_agent_reset()
    print("\n✓ All tests passed!")
