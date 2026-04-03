#!/usr/bin/env python3
"""Quick test to verify tool calls are not accumulated across turns."""

from agent import LoanAnalysisAgent

def test_tool_calls_not_accumulated():
    """Test that respond() only returns tool calls from current turn, not accumulated."""
    agent = LoanAnalysisAgent()
    
    # Mock the client to avoid actual API calls
    class MockResponse:
        def __init__(self, tool_name=None, stop_reason="end_turn"):
            if tool_name:
                class ToolUse:
                    def __init__(self, name):
                        self.type = "tool_use"
                        self.name = name
                        self.input = {"test": "arg"}
                        self.id = f"call_{name}"
                
                class TextBlock:
                    type = "text"
                    text = "Response"
                
                self.content = [ToolUse(tool_name), TextBlock()]
            else:
                class TextBlock:
                    type = "text"
                    text = "Response"
                self.content = [TextBlock()]
            self.stop_reason = stop_reason
    
    # Turn 1: Simulate a call to 'analyze_income'
    agent.client.messages.create = lambda **kwargs: MockResponse("analyze_income")
    response1 = agent.respond("First message")
    
    print(f"Turn 1 tool_calls: {response1['tool_calls']}")
    assert len(response1['tool_calls']) == 1
    assert response1['tool_calls'][0]['name'] == 'analyze_income'
    assert len(agent._accumulated_tool_calls) == 1, "Accumulated should have 1 call after turn 1"
    
    # Turn 2: Simulate a call to 'calculate_dti'
    agent.client.messages.create = lambda **kwargs: MockResponse("calculate_dti")
    response2 = agent.respond("Second message")
    
    print(f"Turn 2 tool_calls: {response2['tool_calls']}")
    # BUG WOULD BE: response2['tool_calls'] contains both analyze_income AND calculate_dti
    # FIX: response2['tool_calls'] contains ONLY calculate_dti
    
    assert len(response2['tool_calls']) == 1, f"Turn 2 should have 1 tool call, got {len(response2['tool_calls'])}"
    assert response2['tool_calls'][0]['name'] == 'calculate_dti', f"Turn 2 should call calculate_dti, got {response2['tool_calls'][0]['name']}"
    assert len(agent._accumulated_tool_calls) == 2, "Accumulated should have 2 calls total"
    
    print("✓ Test passed: tool calls are correctly scoped to current turn only")
    print(f"  Turn 1 returned: {[tc['name'] for tc in response1['tool_calls']]}")
    print(f"  Turn 2 returned: {[tc['name'] for tc in response2['tool_calls']]}")
    print(f"  Accumulated internally: {[tc['name'] for tc in agent._accumulated_tool_calls]}")

if __name__ == "__main__":
    test_tool_calls_not_accumulated()
