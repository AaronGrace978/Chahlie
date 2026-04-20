"""
Pattern Learner
Chahlie learns YOUR coding style, preferences, and patterns over time
"""

import re
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from .memory_manager import ChahlieMemory, Learning


class PatternLearner:
    """
    The Student - Chahlie learns YOUR patterns
    
    Tracks and learns:
    - Your coding style (naming conventions, structure)
    - Your tool preferences (git vs GUI, testing frameworks)
    - Your communication style (verbose vs concise)
    - Your workflow patterns (TDD, refactor-first, etc.)
    """
    
    def __init__(self, memory: ChahlieMemory):
        self.memory = memory
        self.pattern_detectors = {
            "naming_conventions": self._detect_naming_patterns,
            "code_structure": self._detect_structure_patterns,
            "tool_preferences": self._detect_tool_patterns,
            "communication_style": self._detect_communication_patterns,
            "workflow_patterns": self._detect_workflow_patterns,
        }
    
    def analyze_code_sample(self, code: str, filepath: str = None) -> Dict:
        """
        Analyze a code sample to learn user's style
        
        Returns detected patterns with confidence scores
        """
        patterns = {
            "naming": {},
            "structure": {},
            "style": {},
            "timestamp": datetime.now().isoformat()
        }
        
        # Run all pattern detectors
        patterns["naming"] = self._detect_naming_patterns(code)
        patterns["structure"] = self._detect_structure_patterns(code)
        patterns["style"] = self._detect_style_patterns(code)
        
        # Store learnings
        for category, detected in patterns.items():
            if detected and isinstance(detected, dict):
                for pattern_name, (value, confidence) in detected.items():
                    self.memory.add_learning(
                        category=f"code_{category}",
                        pattern=f"User prefers {pattern_name}: {value}",
                        example=filepath or "code sample",
                        confidence=confidence
                    )
        
        return patterns
    
    def _detect_naming_patterns(self, code: str) -> Dict:
        """Detect naming convention preferences"""
        patterns = {}
        
        # Snake case detection (my_variable)
        snake_case = len(re.findall(r'\b[a-z]+_[a-z_]+\b', code))
        # Camel case detection (myVariable)
        camel_case = len(re.findall(r'\b[a-z]+[A-Z][a-zA-Z]*\b', code))
        # Pascal case detection (MyClass)
        pascal_case = len(re.findall(r'\b[A-Z][a-zA-Z]+\b', code))
        
        total = snake_case + camel_case + pascal_case or 1
        
        if snake_case / total > 0.6:
            patterns["variable_style"] = ("snake_case", min(0.9, snake_case / total))
        elif camel_case / total > 0.6:
            patterns["variable_style"] = ("camelCase", min(0.9, camel_case / total))
        
        # Constant detection (ALL_CAPS)
        constants = len(re.findall(r'\b[A-Z]{2,}\b', code))
        if constants > 3:
            patterns["constant_style"] = ("UPPER_CASE", min(0.9, constants / (total + 1)))
        
        return patterns
    
    def _detect_structure_patterns(self, code: str) -> Dict:
        """Detect code structure preferences"""
        patterns = {}
        
        # Function length analysis
        functions = re.findall(r'def \w+\([^)]*\):([\s\S]*?)(?=\n\w|\nclass|\Z)', code)
        if functions:
            avg_lines = sum(len(f.split('\n')) for f in functions) / len(functions)
            if avg_lines < 15:
                patterns["function_size"] = ("short_functions", 0.7)
            elif avg_lines > 50:
                patterns["function_size"] = ("long_functions", 0.7)
            else:
                patterns["function_size"] = ("medium_functions", 0.6)
        
        # Class detection
        classes = len(re.findall(r'\nclass \w+', code))
        if classes > 0:
            patterns["oop_usage"] = ("uses_classes", 0.8)
        
        # Type hints detection
        type_hints = len(re.findall(r':\s*(str|int|float|bool|List|Dict|Optional)', code))
        if type_hints > 3:
            patterns["type_hints"] = ("uses_type_hints", min(0.9, type_hints / 10))
        
        # Docstring detection
        docstrings = len(re.findall(r'"""[\s\S]*?"""', code))
        if docstrings > 2:
            patterns["documentation"] = ("uses_docstrings", min(0.9, docstrings / 5))
        
        return patterns
    
    def _detect_style_patterns(self, code: str) -> Dict:
        """Detect coding style preferences"""
        patterns = {}
        
        # Quote style
        single_quotes = code.count("'")
        double_quotes = code.count('"')
        if single_quotes > double_quotes * 1.5:
            patterns["quote_style"] = ("single_quotes", 0.7)
        elif double_quotes > single_quotes * 1.5:
            patterns["quote_style"] = ("double_quotes", 0.7)
        
        # Import style
        from_imports = len(re.findall(r'\nfrom [\w.]+ import', code))
        import_lines = len(re.findall(r'\nimport \w+', code))
        if from_imports > import_lines * 1.5:
            patterns["import_style"] = ("from_imports", 0.6)
        
        return patterns
    
    def _detect_tool_patterns(self, tool_uses: List[Dict]) -> Dict:
        """Detect tool usage preferences"""
        patterns = {}
        
        tool_counts = defaultdict(int)
        for tool_use in tool_uses:
            tool_name = tool_use.get("tool", "unknown")
            tool_counts[tool_name] += 1
        
        # Most used tools
        if tool_counts:
            most_used = max(tool_counts, key=tool_counts.get)
            patterns["preferred_tool"] = (most_used, 0.6)
        
        return patterns
    
    def _detect_communication_patterns(self, messages: List[Dict]) -> Dict:
        """Detect user communication style"""
        patterns = {}
        
        if not messages:
            return patterns
        
        # Average message length
        avg_length = sum(len(m.get("content", "")) for m in messages) / len(messages)
        
        if avg_length < 50:
            patterns["communication"] = ("concise", 0.7)
        elif avg_length > 200:
            patterns["communication"] = ("detailed", 0.7)
        else:
            patterns["communication"] = ("balanced", 0.6)
        
        # Question frequency
        questions = sum(1 for m in messages if "?" in m.get("content", ""))
        if questions / len(messages) > 0.5:
            patterns["interaction"] = ("question_heavy", 0.6)
        
        return patterns
    
    def _detect_workflow_patterns(self, sessions: List) -> Dict:
        """Detect workflow patterns from session history"""
        patterns = {}
        
        if not sessions:
            return patterns
        
        # Test-driven development detection
        test_files = sum(
            1 for s in sessions 
            for f in s.files_modified 
            if 'test' in f.lower()
        )
        
        if test_files > len(sessions) * 0.5:
            patterns["workflow"] = ("test_driven", 0.7)
        
        # Refactor patterns
        refactor_keywords = ["refactor", "clean", "restructure", "improve"]
        refactor_sessions = sum(
            1 for s in sessions 
            if any(kw in s.summary.lower() for kw in refactor_keywords)
        )
        
        if refactor_sessions > len(sessions) * 0.3:
            patterns["workflow"] = ("refactor_focused", 0.6)
        
        return patterns
    
    def get_user_profile(self) -> Dict:
        """
        Build a comprehensive user profile from all learnings
        
        This is Chahlie's "understanding" of the user
        """
        learnings = self.memory.get_learnings()
        
        profile = {
            "coding_style": {},
            "tool_preferences": {},
            "communication_style": {},
            "workflow": {},
            "generated_at": datetime.now().isoformat(),
            "confidence": 0.0
        }
        
        # Group learnings by category
        for learning in learnings:
            category = learning.category
            pattern = learning.pattern
            
            if category.startswith("code_"):
                profile["coding_style"][category] = pattern
            elif category.startswith("tool_"):
                profile["tool_preferences"][category] = pattern
            elif category.startswith("user_") or category.startswith("communication"):
                profile["communication_style"][category] = pattern
            elif category.startswith("workflow"):
                profile["workflow"][category] = pattern
        
        # Calculate overall confidence
        total_learnings = len(learnings)
        high_confidence = sum(1 for l in learnings if l.confidence > 0.7)
        
        if total_learnings > 0:
            profile["confidence"] = min(1.0, (total_learnings / 50) * 0.5 + (high_confidence / total_learnings) * 0.5)
        
        return profile
    
    def get_personalized_suggestions(self) -> List[str]:
        """
        Get suggestions based on learned patterns
        
        "Hey, I noticed you like X, want me to do more of that?"
        """
        profile = self.get_user_profile()
        suggestions = []
        
        if profile["coding_style"].get("code_naming") == "User prefers variable_style: snake_case":
            suggestions.append("I'll stick with snake_case for variables, boss")
        
        if profile["coding_style"].get("code_style") == "User prefers type_hints: uses_type_hints":
            suggestions.append("I'll include type hints in all new code")
        
        if profile["communication_style"].get("communication") == "User prefers communication: concise":
            suggestions.append("I'll keep my responses brief and to the point")
        
        if profile["workflow"].get("workflow") == "User prefers workflow: test_driven":
            suggestions.append("I'll write tests first, then implementation")
        
        return suggestions
    
    def adapt_to_feedback(self, task: str, feedback: str, sentiment: str):
        """
        Adapt patterns based on explicit feedback
        
        User says: "I don't like how you did X" -> learn from it
        """
        sentiment_lower = sentiment.lower()
        
        if sentiment_lower in ["negative", "frustrated"]:
            # Learn what NOT to do
            self.memory.add_learning(
                category="avoid",
                pattern=f"Avoid: {task}",
                example=feedback[:300],
                confidence=0.8
            )
        elif sentiment_lower in ["positive", "happy"]:
            # Learn what TO do
            self.memory.add_learning(
                category="emulate",
                pattern=f"Continue: {task}",
                example=feedback[:300],
                confidence=0.7
            )
    
    def export_profile(self, filepath: str = None) -> str:
        """Export user profile to file"""
        if not filepath:
            filepath = self.memory.memory_dir / "user_profile.json"
        
        profile = self.get_user_profile()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            import json
            json.dump(profile, f, indent=2, default=str)
        
        return str(filepath)
