#!/usr/bin/env python3
"""
Quick test for Chahlie's Memory System
"""

from chahlie.memory import ChahlieMemory, ReflectionEngine, PatternLearner

print("Testing Memory System...")

# Test initialization
memory = ChahlieMemory()
print("✓ Memory initialized")

# Test session
memory.start_session()
memory.track_message("user", "Create API")
memory.track_tool_use("write_file", {"path": "api.py"}, True)
session = memory.end_session("Test session")
print(f"✓ Session tracked: {session.id}")

# Test learning
memory.add_learning("test", "Test pattern", "example", 0.8)
print(f"✓ Learning added")

# Test reflection
reflection_engine = ReflectionEngine(memory)
reflection = reflection_engine.reflect_on_tool_use("write_file", {}, True, "OK")
print(f"✓ Reflection working")

# Test pattern learner
pattern_learner = PatternLearner(memory)
profile = pattern_learner.get_user_profile()
print(f"✓ Profile generated (confidence: {profile['confidence']:.0%})")

# Summary
summary = memory.get_summary()
print(f"\nSummary: {summary['total_sessions']} sessions, {summary['total_learnings']} learnings")

print("\nMEMORY SYSTEM WORKING!")
