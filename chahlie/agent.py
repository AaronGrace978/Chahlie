"""
Chahlie's Agent Core
The brain that makes it all work - supports Ollama Cloud, local Ollama, and Anthropic
"""

import json
import os
from typing import Generator, Optional
from dataclasses import dataclass

from .config import (
    BACKEND, 
    ANTHROPIC_API_KEY, ANTHROPIC_MODEL,
    OLLAMA_CLOUD_HOST, OLLAMA_CLOUD_API_KEY, OLLAMA_LOCAL_HOST, OLLAMA_MODEL,
    MAX_TOKENS
)
from .personality import SYSTEM_PROMPT, get_working, get_success, get_error
from .tools import TOOL_DEFINITIONS, execute_tool, ToolResult


@dataclass
class AgentEvent:
    """Events emitted by the agent during processing"""
    type: str  # 'thinking', 'text', 'tool_use', 'tool_result', 'error', 'done'
    content: str
    data: Optional[dict] = None


class ChahlieAgent:
    """
    The Chahlie Agent - Boston's finest coding assistant
    Supports Ollama Cloud, local Ollama, and Anthropic backends
    """
    
    def __init__(self, backend: str = None):
        self.backend = backend or BACKEND
        self.conversation_history = []
        
        if self.backend == "anthropic":
            from anthropic import Anthropic
            self.client = Anthropic(api_key=ANTHROPIC_API_KEY)
            self.model = ANTHROPIC_MODEL
        elif self.backend == "ollama-cloud":
            from ollama import Client
            self.client = Client(
                host=OLLAMA_CLOUD_HOST,
                headers={'Authorization': f'Bearer {OLLAMA_CLOUD_API_KEY}'}
            )
            self.model = OLLAMA_MODEL
        else:  # ollama-local
            from ollama import Client
            self.client = Client(host=OLLAMA_LOCAL_HOST)
            self.model = OLLAMA_MODEL
    
    def reset(self):
        """Clear conversation history"""
        self.conversation_history = []
    
    def _call_ollama(self, messages: list) -> dict:
        """Call Ollama API with tool support (works with both Cloud and local)"""
        # Convert tools to Ollama format
        tools = []
        for tool in TOOL_DEFINITIONS:
            tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"]
                }
            })
        
        # Use official Ollama Python library
        response = self.client.chat(
            model=self.model,
            messages=messages,
            tools=tools,
            stream=False
        )
        
        # Convert response to dict format
        return {
            "message": {
                "role": response.message.role,
                "content": response.message.content or "",
                "tool_calls": [
                    {
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in (response.message.tool_calls or [])
                ]
            }
        }
    
    def _process_ollama(self, user_message: str) -> Generator[AgentEvent, None, None]:
        """Process with Ollama backend"""
        # Build messages with system prompt
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        # Add conversation history
        for msg in self.conversation_history:
            messages.append(msg)
        
        # Add user message
        messages.append({"role": "user", "content": user_message})
        self.conversation_history.append({"role": "user", "content": user_message})
        
        # Agent loop
        while True:
            yield AgentEvent(type="thinking", content=get_working())
            
            try:
                response = self._call_ollama(messages)
            except Exception as e:
                yield AgentEvent(type="error", content=f"Ollama Error: {str(e)}")
                return
            
            message = response.get("message", {})
            content = message.get("content", "")
            tool_calls = message.get("tool_calls", [])
            
            # Add assistant response to history
            assistant_msg = {"role": "assistant", "content": content}
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls
            messages.append(assistant_msg)
            self.conversation_history.append(assistant_msg)
            
            # Emit text if any
            if content:
                yield AgentEvent(type="text", content=content)
            
            # If no tool calls, we're done
            if not tool_calls:
                yield AgentEvent(type="done", content=get_success())
                return
            
            # Process tool calls
            for tool_call in tool_calls:
                func = tool_call.get("function", {})
                tool_name = func.get("name", "")
                tool_args = func.get("arguments", {})
                
                # Handle string arguments (some models return JSON string)
                if isinstance(tool_args, str):
                    try:
                        tool_args = json.loads(tool_args)
                    except:
                        tool_args = {}
                
                # Emit tool use event
                yield AgentEvent(
                    type="tool_use",
                    content=f"Using {tool_name}",
                    data={"tool": tool_name, "input": tool_args}
                )
                
                # Execute the tool
                result = execute_tool(tool_name, tool_args)
                
                # Emit tool result event
                yield AgentEvent(
                    type="tool_result",
                    content=result.output if result.success else result.error,
                    data={
                        "tool": tool_name,
                        "success": result.success,
                        "output": result.output,
                        "error": result.error
                    }
                )
                
                # Add tool result to messages
                tool_result_msg = {
                    "role": "tool",
                    "content": result.output if result.success else f"Error: {result.error}"
                }
                messages.append(tool_result_msg)
                self.conversation_history.append(tool_result_msg)
    
    def _process_anthropic(self, user_message: str) -> Generator[AgentEvent, None, None]:
        """Process with Anthropic backend"""
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Agent loop
        while True:
            yield AgentEvent(type="thinking", content=get_working())
            
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=MAX_TOKENS,
                    system=SYSTEM_PROMPT,
                    tools=TOOL_DEFINITIONS,
                    messages=self.conversation_history
                )
            except Exception as e:
                yield AgentEvent(type="error", content=f"API Error: {str(e)}")
                return
            
            # Process the response
            assistant_content = []
            has_tool_use = False
            text_content = ""
            
            for block in response.content:
                if block.type == "text":
                    text_content += block.text
                    assistant_content.append({
                        "type": "text",
                        "text": block.text
                    })
                elif block.type == "tool_use":
                    has_tool_use = True
                    assistant_content.append({
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input
                    })
            
            # Emit text if any
            if text_content:
                yield AgentEvent(type="text", content=text_content)
            
            # Add assistant response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_content
            })
            
            # If no tool use, we're done
            if not has_tool_use or response.stop_reason == "end_turn":
                if not has_tool_use:
                    yield AgentEvent(type="done", content=get_success())
                    return
            
            # Process tool calls
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    yield AgentEvent(
                        type="tool_use",
                        content=f"Using {block.name}",
                        data={"tool": block.name, "input": block.input}
                    )
                    
                    result = execute_tool(block.name, block.input)
                    
                    yield AgentEvent(
                        type="tool_result",
                        content=result.output if result.success else result.error,
                        data={
                            "tool": block.name,
                            "success": result.success,
                            "output": result.output,
                            "error": result.error
                        }
                    )
                    
                    if result.success:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result.output
                        })
                    else:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Error: {result.error}",
                            "is_error": True
                        })
            
            self.conversation_history.append({
                "role": "user",
                "content": tool_results
            })
            
            if response.stop_reason == "end_turn":
                yield AgentEvent(type="done", content=get_success())
                return
    
    def process(self, user_message: str) -> Generator[AgentEvent, None, None]:
        """Process a user message and yield events"""
        if self.backend == "anthropic":
            yield from self._process_anthropic(user_message)
        else:
            # Both ollama-cloud and ollama-local use the same processing
            yield from self._process_ollama(user_message)
    
    def chat(self, user_message: str) -> str:
        """Simple synchronous chat - returns the final text response"""
        final_text = ""
        for event in self.process(user_message):
            if event.type == "text":
                final_text += event.content
        return final_text
