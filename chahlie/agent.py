"""
Chahlie's Agent Core - NOW WITH MEMORY!
The brain that makes it all work - supports Ollama Cloud, local Ollama, and Anthropic
NOW WITH RECURSIVE SELF-IMPROVEMENT!
"""

import json
import os
from typing import Generator, Optional
from dataclasses import dataclass
from datetime import datetime

from .config import (
    BACKEND, 
    ANTHROPIC_API_KEY, ANTHROPIC_MODEL,
    OLLAMA_CLOUD_HOST, OLLAMA_CLOUD_API_KEY, OLLAMA_LOCAL_HOST, OLLAMA_MODEL,
    MAX_TOKENS
)
from .personality import SYSTEM_PROMPT, get_working, get_success, get_error
from .tools import TOOL_DEFINITIONS, execute_tool, ToolResult
from .memory import ChahlieMemory, ReflectionEngine, PatternLearner


@dataclass
class AgentEvent:
    """Events emitted by the agent during processing"""
    type: str  # 'thinking', 'text', 'tool_use', 'tool_result', 'error', 'done', 'reflection'
    content: str
    data: Optional[dict] = None


class ChahlieAgent:
    """
    The Chahlie Agent - Boston's finest coding assistant
    NOW WITH MEMORY AND SELF-IMPROVEMENT!
    
    Supports Ollama Cloud, local Ollama, and Anthropic backends
    """
    
    def __init__(self, backend: str = None, enable_memory: bool = True):
        self.backend = backend or BACKEND
        self.conversation_history = []
        self.enable_memory = enable_memory
        
        # Initialize memory system
        if self.enable_memory:
            self.memory = ChahlieMemory()
            self.reflection_engine = ReflectionEngine(self.memory)
            self.pattern_learner = PatternLearner(self.memory)
            self.memory.start_session()
        else:
            self.memory = None
            self.reflection_engine = None
            self.pattern_learner = None
        
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
        
        # Track current task for reflection
        self.current_task = None
        self.task_start_time = None
    
    def reset(self):
        """Clear conversation history and end session"""
        self.conversation_history = []
        if self.memory:
            self.memory.end_session("Session cleared by user")
            self.memory.start_session()
    
    def _get_enhanced_system_prompt(self) -> str:
        """
        Enhance the system prompt with learned patterns
        
        This is where Chahlie ADAPTS based on memory
        """
        base_prompt = SYSTEM_PROMPT
        
        if not self.memory:
            return base_prompt
        
        # Get user profile and learnings
        profile = self.pattern_learner.get_user_profile()
        learnings = self.memory.get_learnings()
        
        # Build adaptation section
        adaptations = []
        
        if profile["coding_style"]:
            adaptations.append("\n\nUSER CODING STYLE (learned patterns):")
            for category, pattern in profile["coding_style"].items():
                adaptations.append(f"- {pattern}")
        
        if profile["communication_style"]:
            adaptations.append("\n\nUSER COMMUNICATION PREFERENCES:")
            for category, pattern in profile["communication_style"].items():
                if "concise" in pattern.lower():
                    adaptations.append("- Keep responses brief and direct")
                elif "detailed" in pattern.lower():
                    adaptations.append("- Provide thorough explanations")
        
        if profile["workflow"]:
            adaptations.append("\n\nUSER WORKFLOW PATTERNS:")
            for category, pattern in profile["workflow"].items():
                adaptations.append(f"- {pattern}")
        
        # Add recent reflections
        recent_reflections = self.memory.get_reflections(limit=5)
        if recent_reflections:
            adaptations.append("\n\nRECENT LEARNINGS (from self-reflection):")
            for ref in recent_reflections:
                if ref.get("learnings"):
                    for learning in ref["learnings"]:
                        adaptations.append(f"- {learning.get('pattern', '')}")
        
        # Combine base prompt with adaptations
        if adaptations:
            return base_prompt + "\n\n".join(adaptations)
        
        return base_prompt
    
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
        # Track message in memory
        if self.memory:
            self.memory.track_message("user", user_message)
        
        # Build messages with ENHANCED system prompt (includes learnings)
        messages = [{"role": "system", "content": self._get_enhanced_system_prompt()}]
        
        # Add conversation history
        for msg in self.conversation_history:
            messages.append(msg)
        
        # Add user message
        messages.append({"role": "user", "content": user_message})
        self.conversation_history.append({"role": "user", "content": user_message})
        
        # Track task start
        self.current_task = user_message[:200]
        self.task_start_time = datetime.now()
        
        # Agent loop
        tool_results = []
        while True:
            yield AgentEvent(type="thinking", content=get_working())
            
            try:
                response = self._call_ollama(messages)
            except Exception as e:
                yield AgentEvent(type="error", content=f"Ollama Error: {str(e)}")
                if self.memory:
                    self.reflection_engine.reflect_on_tool_use(
                        "api_call", {}, False, str(e)
                    )
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
            
            # Track in memory
            if self.memory:
                self.memory.track_message("assistant", content)
            
            # Emit text if any
            if content:
                yield AgentEvent(type="text", content=content)
            
            # If no tool calls, we're done
            if not tool_calls:
                yield AgentEvent(type="done", content=get_success())
                
                # Reflect on task completion
                if self.memory:
                    self.reflection_engine.reflect_on_user_feedback(
                        user_message, "neutral"  # Could analyze sentiment
                    )
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
                
                # Track tool use
                if self.memory:
                    self.memory.track_tool_use(tool_name, tool_args, True)
                
                # Execute the tool
                result = execute_tool(tool_name, tool_args)
                
                # Track result
                if self.memory:
                    self.memory.track_tool_use(tool_name, tool_args, result.success)
                    if tool_name == "write_file":
                        self.memory.track_file_modified(tool_args.get("path", "unknown"))
                    elif tool_name == "run_command":
                        self.memory.track_command(tool_args.get("command", ""), result.success)
                
                # Reflect on tool result IMMEDIATELY (recursive learning!)
                if self.memory:
                    reflection = self.reflection_engine.reflect_on_tool_use(
                        tool_name, tool_args, result.success, result.output or result.error
                    )
                    
                    # If reflection found a pattern, emit it
                    if reflection.get("insights"):
                        yield AgentEvent(
                            type="reflection",
                            content=f"💡 Learning: {reflection['insights'][0]}",
                            data=reflection
                        )
                
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
                
                tool_results.append(result)
                
                # Add tool result to messages
                tool_result_msg = {
                    "role": "tool",
                    "content": result.output if result.success else f"Error: {result.error}"
                }
                messages.append(tool_result_msg)
                self.conversation_history.append(tool_result_msg)
    
    def _process_anthropic(self, user_message: str) -> Generator[AgentEvent, None, None]:
        """Process with Anthropic backend"""
        # Track message in memory
        if self.memory:
            self.memory.track_message("user", user_message)
        
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Track task start
        self.current_task = user_message[:200]
        self.task_start_time = datetime.now()
        
        # Agent loop
        while True:
            yield AgentEvent(type="thinking", content=get_working())
            
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=MAX_TOKENS,
                    system=self._get_enhanced_system_prompt(),
                    tools=TOOL_DEFINITIONS,
                    messages=self.conversation_history
                )
            except Exception as e:
                yield AgentEvent(type="error", content=f"API Error: {str(e)}")
                if self.memory:
                    self.reflection_engine.reflect_on_tool_use("api_call", {}, False, str(e))
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
            
            # Track in memory
            if self.memory:
                self.memory.track_message("assistant", text_content)
            
            # Add assistant response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_content
            })
            
            # If no tool use, we're done
            if not has_tool_use or response.stop_reason == "end_turn":
                if not has_tool_use:
                    yield AgentEvent(type="done", content=get_success())
                    
                    # Reflect on task
                    if self.memory:
                        self.reflection_engine.reflect_on_user_feedback(
                            user_message, "neutral"
                        )
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
                    
                    # Track tool use
                    if self.memory:
                        self.memory.track_tool_use(block.name, block.input, True)
                    
                    result = execute_tool(block.name, block.input)
                    
                    # Track result
                    if self.memory:
                        self.memory.track_tool_use(block.name, block.input, result.success)
                        if block.name == "write_file":
                            self.memory.track_file_modified(block.input.get("path", "unknown"))
                        elif block.name == "run_command":
                            self.memory.track_command(block.input.get("command", ""), result.success)
                    
                    # Reflect on tool result
                    if self.memory:
                        reflection = self.reflection_engine.reflect_on_tool_use(
                            block.name, block.input, result.success, result.output or result.error
                        )
                        if reflection.get("insights"):
                            yield AgentEvent(
                                type="reflection",
                                content=f"💡 Learning: {reflection['insights'][0]}",
                                data=reflection
                            )
                    
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
            yield from self._process_ollama(user_message)
    
    def chat(self, user_message: str) -> str:
        """Simple synchronous chat - returns the final text response"""
        final_text = ""
        for event in self.process(user_message):
            if event.type == "text":
                final_text += event.content
        return final_text
    
    def get_memory_summary(self) -> dict:
        """Get a summary of what Chahlie has learned"""
        if not self.memory:
            return {"enabled": False}
        
        return {
            "enabled": True,
            "summary": self.memory.get_summary(),
            "user_profile": self.pattern_learner.get_user_profile(),
            "improvement_plan": self.reflection_engine.generate_improvement_plan()
        }
    
    def __del__(self):
        """Cleanup - save session on exit"""
        if self.memory and self.memory.current_session_start:
            self.memory.end_session("Session ended")
