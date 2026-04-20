"""
Reflection Engine
Chahlie thinks about his own performance and learns from it
"""

import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from .memory_manager import ChahlieMemory, Session, Learning


class ReflectionEngine:
    """
    The Conscience - Chahlie reflects on his own performance
    
    After each task/session, analyzes:
    - What went well
    - What went wrong
    - What could be improved
    - Patterns to learn from
    """
    
    def __init__(self, memory: ChahlieMemory):
        self.memory = memory
        self.reflection_prompts = {
            "success": [
                "What worked particularly well here?",
                "Which approach was most effective?",
                "What should I do more of?",
                "What made this successful?",
            ],
            "failure": [
                "What went wrong?",
                "Where did I misunderstand the task?",
                "What tool or approach failed?",
                "What should I do differently next time?",
            ],
            "improvement": [
                "How could this have been better?",
                "What was inefficient?",
                "Did I overcomplicate anything?",
                "What would make this faster/cleaner?",
            ],
            "pattern": [
                "Have I seen this before?",
                "Is this a recurring issue?",
                "What's the underlying pattern?",
                "How does this connect to other learnings?",
            ]
        }
    
    def reflect_on_session(self, session: Session) -> Dict:
        """
        Reflect on a completed session
        
        Returns a reflection dict with insights and learnings
        """
        reflection = {
            "session_id": session.id,
            "timestamp": datetime.now().isoformat(),
            "overall_success": session.success_rate,
            "strengths": [],
            "weaknesses": [],
            "learnings": [],
            "action_items": [],
            "pattern_observations": []
        }
        
        # Analyze success rate
        if session.success_rate >= 0.9:
            reflection["strengths"].append("High success rate on tool usage")
        elif session.success_rate < 0.7:
            reflection["weaknesses"].append(f"Low tool success rate: {session.success_rate:.1%}")
            reflection["action_items"].append("Review tool usage patterns")
        
        # Analyze tool usage
        if len(session.tools_used) > 10:
            reflection["pattern_observations"].append("Used many different tools - complex task")
        
        # Analyze file modifications
        if len(session.files_modified) > 5:
            reflection["pattern_observations"].append("Modified many files - large scope change")
            reflection["learnings"].append({
                "category": "workflow",
                "pattern": "Large refactors may benefit from planning phase",
                "confidence": 0.6
            })
        
        # Analyze commands run
        failed_commands = [c for c in session.commands_run if "error" in c.lower() or "fail" in c.lower()]
        if failed_commands:
            reflection["weaknesses"].append(f"Command execution issues: {len(failed_commands)} failures")
            reflection["action_items"].append("Double-check commands before running")
        
        # Generate learnings
        if reflection["strengths"]:
            for strength in reflection["strengths"]:
                self.memory.add_learning(
                    category="strength",
                    pattern=strength,
                    example=f"Session {session.id}",
                    confidence=0.7
                )
        
        if reflection["weaknesses"]:
            for weakness in reflection["weaknesses"]:
                self.memory.add_learning(
                    category="improvement_area",
                    pattern=weakness,
                    example=f"Session {session.id}",
                    confidence=0.5
                )
        
        # Save reflection
        self.memory.add_reflection(reflection)
        
        return reflection
    
    def reflect_on_tool_use(self, tool_name: str, arguments: Dict, success: bool, output: str) -> Dict:
        """
        Reflect on a single tool usage
        
        Quick reflection for immediate learning
        """
        reflection = {
            "type": "tool_reflection",
            "tool": tool_name,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "insights": []
        }
        
        if success:
            reflection["insights"].append(f"{tool_name} executed successfully")
            # Learn successful patterns
            self.memory.add_learning(
                category="tool_success",
                pattern=f"{tool_name} works well with these arguments",
                example=str(arguments)[:200],
                confidence=0.6
            )
        else:
            reflection["insights"].append(f"{tool_name} failed - needs review")
            reflection["error_analysis"] = output[:500] if output else "No output"
            
            # Learn from failures
            self.memory.add_learning(
                category="tool_failure",
                pattern=f"{tool_name} failed with these arguments",
                example=str(arguments)[:200],
                confidence=0.8  # Higher confidence on failures
            )
        
        self.memory.add_reflection(reflection)
        return reflection
    
    def reflect_on_user_feedback(self, feedback: str, sentiment: str = "neutral") -> Dict:
        """
        Reflect on explicit user feedback
        
        User says: "Good job!" or "That's not what I meant"
        """
        reflection = {
            "type": "user_feedback",
            "feedback": feedback,
            "sentiment": sentiment,
            "timestamp": datetime.now().isoformat(),
            "learnings": []
        }
        
        sentiment_lower = sentiment.lower()
        
        if sentiment_lower in ["positive", "happy", "satisfied"]:
            reflection["learnings"].append("User was satisfied - continue this approach")
            self.memory.add_learning(
                category="user_preference",
                pattern="This approach satisfies the user",
                example=feedback[:200],
                confidence=0.7
            )
        elif sentiment_lower in ["negative", "frustrated", "disappointed"]:
            reflection["learnings"].append("User was not satisfied - adjust approach")
            self.memory.add_learning(
                category="user_preference",
                pattern="This approach did not satisfy the user",
                example=feedback[:200],
                confidence=0.8
            )
            reflection["action_items"] = [
                "Ask clarifying questions",
                "Slow down and confirm understanding",
                "Offer alternative approaches"
            ]
        
        self.memory.add_reflection(reflection)
        return reflection
    
    def generate_improvement_plan(self) -> Dict:
        """
        Generate a self-improvement plan based on all reflections
        
        This is Chahlie's "New Year's Resolution" - what to work on
        """
        reflections = self.memory.get_reflections(limit=50)
        
        # Count patterns
        weakness_counts = {}
        strength_counts = {}
        
        for ref in reflections:
            for weakness in ref.get("weaknesses", []):
                weakness_counts[weakness] = weakness_counts.get(weakness, 0) + 1
            for strength in ref.get("strengths", []):
                strength_counts[strength] = strength_counts.get(strength, 0) + 1
        
        # Top areas to improve
        top_weaknesses = sorted(weakness_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_strengths = sorted(strength_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        plan = {
            "generated_at": datetime.now().isoformat(),
            "focus_areas": [
                {
                    "area": weakness,
                    "occurrences": count,
                    "priority": "high" if count > 3 else "medium",
                    "suggested_action": self._get_improvement_action(weakness)
                }
                for weakness, count in top_weaknesses
            ],
            "continue_doing": [
                {
                    "area": strength,
                    "occurrences": count
                }
                for strength, count in top_strengths
            ],
            "total_reflections_analyzed": len(reflections)
        }
        
        return plan
    
    def _get_improvement_action(self, weakness: str) -> str:
        """Suggest an action for a given weakness"""
        actions = {
            "tool": "Review tool documentation and argument formats",
            "command": "Add validation step before running commands",
            "understanding": "Ask more clarifying questions",
            "efficiency": "Plan approach before executing",
            "communication": "Provide more detailed explanations"
        }
        
        for key, action in actions.items():
            if key in weakness.lower():
                return action
        
        return "Review and adjust approach"
    
    def get_session_insights(self, session_id: str) -> Optional[Dict]:
        """Get insights for a specific session"""
        reflections = self.memory.get_reflections(limit=100)
        
        for ref in reflections:
            if ref.get("session_id") == session_id:
                return ref
        
        return None
