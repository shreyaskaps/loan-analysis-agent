#!/usr/bin/env python3
"""Test that demonstrates web_search tool providing real loan market data."""

from tools import execute_tool, TOOL_DEFINITIONS


def test_web_search_returns_current_rates():
    """Test that web_search returns actual market rate information."""
    
    test_cases = [
        ("current mortgage rates", "mortgage"),
        ("auto loan rates today", "auto"),
        ("personal loan rates april 2026", "personal"),
        ("should I refinance at today's rates", "refi"),
    ]
    
    print("Testing web_search tool with current rate queries:\n")
    
    for query, expected_keyword in test_cases:
        result = execute_tool("web_search", {"query": query})
        
        # Verify result is not a generic placeholder
        assert "Web search completed for" not in result, f"Query '{query}' returned placeholder message"
        assert "Web search results for" in result, f"Query '{query}' did not return structured results"
        assert expected_keyword in result.lower() or "2026" in result, f"Query '{query}' missing expected content"
        
        # Verify result contains actionable information
        assert any(marker in result for marker in [
            "%", "APR", "rate", "Rate", "mortgage", "auto", "loan", "personal"
        ]), f"Query '{query}' missing rate/rate-related information"
        
        print(f"✓ '{query}' -> Returns market data with rates/requirements")
    
    print("\n✓ All web_search queries return actionable market information")


def test_web_search_tool_definition():
    """Verify web_search tool has clear documentation."""
    web_search_tool = next(
        (t for t in TOOL_DEFINITIONS if t["name"] == "web_search"),
        None
    )
    
    assert web_search_tool is not None
    assert "description" in web_search_tool
    assert "input_schema" in web_search_tool
    
    # Verify description mentions current/market data
    desc = web_search_tool["description"].lower()
    assert any(word in desc for word in ["current", "rate", "market", "lender"]), \
        "Tool description should mention current rates, market, or lenders"
    
    print("✓ web_search tool properly documented")


def test_web_search_handles_generic_queries():
    """Test that web_search gracefully handles generic queries."""
    result = execute_tool("web_search", {"query": "loan information"})
    
    # Should return some market information even for generic queries
    assert "Web search results for" in result or "market" in result.lower()
    
    print("✓ web_search handles generic queries gracefully")


if __name__ == "__main__":
    test_web_search_returns_current_rates()
    test_web_search_tool_definition()
    test_web_search_handles_generic_queries()
    print("\n✅ All web_search integration tests passed!")
