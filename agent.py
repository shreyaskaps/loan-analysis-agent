"""Loan analysis agent with multimodal document processing.

Handles PDFs, scanned/handwritten documents, images, and spreadsheets
by converting them to Claude Vision content blocks. Compatible with
the Ashr SDK's respond()/reset() interface for evaluation.
"""

import os
import re
import anthropic
from tools import TOOL_DEFINITIONS, execute_tool
from document_loader import load_documents

SYSTEM_PROMPT = """You are a helpful assistant. Before calling any tools, think through what information you need and which tool will provide it. Then call the appropriate tool."""

# Regex to detect file paths in messages
FILE_PATH_PATTERN = re.compile(
    r'(?:^|\s|["\'])(/[^\s"\']+\.(?:pdf|png|jpg|jpeg|gif|webp|csv|tsv|xlsx|xls|bmp|tiff|tif))',
    re.IGNORECASE,
)


class LoanAnalysisAgent:
    """Ashr-compatible loan analysis agent with multimodal document support."""

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.Anthropic()
        self.messages: list[dict] = []
        self.model = model
        self._accumulated_tool_calls: list[dict] = []

    def reset(self):
        """Clear conversation state between scenarios."""
        self.messages = []
        self._accumulated_tool_calls = []

    def respond(self, message: str) -> dict:
        """Process a message and return text + tool_calls.

        Detects file paths in the message and loads them as multimodal
        content blocks. Runs the Claude tool-calling loop until complete.
        Accumulates tool calls across respond() calls.
        """
        # Detect file paths in message
        file_paths = FILE_PATH_PATTERN.findall(message)

        # Build content blocks for this message
        content_blocks: list[dict] = []

        if file_paths:
            # Add the text portion of the message
            content_blocks.append({"type": "text", "text": message})
            # Load each document and append its content blocks
            doc_blocks = load_documents(file_paths)
            content_blocks.extend(doc_blocks)
        else:
            # Plain text message
            content_blocks = [{"type": "text", "text": message}]

        self.messages.append({"role": "user", "content": content_blocks})

        new_tool_calls = []
        final_text = ""

        # Agent loop: keep going until no more tool calls
        for _ in range(15):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOL_DEFINITIONS,
                messages=self.messages,
            )

            # Collect text and tool use blocks
            assistant_content = response.content
            text_parts = []
            tool_uses = []

            for block in assistant_content:
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_uses.append(block)

            # Append assistant message
            self.messages.append({"role": "assistant", "content": assistant_content})

            if text_parts:
                final_text = "\n".join(text_parts)

            if not tool_uses:
                break

            # Execute tools and add results
            tool_results = []
            for tool_use in tool_uses:
                new_tool_calls.append({
                    "name": tool_use.name,
                    "arguments": tool_use.input,
                })
                result = execute_tool(tool_use.name, tool_use.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": result,
                })

            self.messages.append({"role": "user", "content": tool_results})

            if response.stop_reason == "end_turn":
                break

        self._accumulated_tool_calls.extend(new_tool_calls)

        return {
            "text": final_text,
            "tool_calls": list(self._accumulated_tool_calls),
        }
