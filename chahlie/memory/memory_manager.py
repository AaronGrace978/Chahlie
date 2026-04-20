"""
Chahlie Memory Manager
Handles persistent storage of sessions, learnings, and project context
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class Session:
    """A single coding session"""
    id: str
    timestamp: str
    duration_seconds: int
    user_messages: int
    agent_responses: int
    tools_used: List[str]
    files_modified: List[str]
    commands_run: List[str]
    success_rate: float
    summary: str
    key_decisions: List[str]


@dataclass
class Learning:
    """A learned pattern or preference"""
    id: str
    timestamp: str
    category: str  # 'coding_style', 'tool_preference', 'communication', 'workflow'
    pattern: str
    example: str
    confidence: float  # 0.0 to 1.0
    times_seen: int
    last_reinforced: str


@dataclass
class ProjectContext:
    """Project-level knowledge"""
    name: str
    path: str
    language: str
    framework: str
    architecture_notes: List[str]
    common_patterns: List[str]
    gotchas: List[str]  # "Don't run migration without backup"
    todos: List[Dict[str, Any]]
    last_updated: str


class ChahlieMemory:
    """
    The Memory System - Chahlie's long-term knowledge base
    
    Stores:
    - Session history
    - Learned patterns about the user
    - Project context and decisions
    - Self-reflection data for improvement
    """
    
    def __init__(self, project_path: str = None):
        self.project_path = Path(project_path) if project_path else Path.cwd()
        self.memory_dir = self.project_path / ".chahlie" / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        # File paths
        self.sessions_file = self.memory_dir / "sessions.json"
        self.learnings_file = self.memory_dir / "learnings.json"
        self.context_file = self.memory_dir / "context.json"
        self.reflections_file = self.memory_dir / "reflections.json"
        
        # Load existing data (rehydrate dicts into dataclass instances)
        self.sessions: List[Session] = [
            Session(**s) if isinstance(s, dict) else s
            for s in self._load_json(self.sessions_file, [])
        ]
        self.learnings: List[Learning] = [
            Learning(**l) if isinstance(l, dict) else l
            for l in self._load_json(self.learnings_file, [])
        ]
        ctx_raw = self._load_json(self.context_file, None)
        self.context: Optional[ProjectContext] = (
            ProjectContext(**ctx_raw) if isinstance(ctx_raw, dict) else ctx_raw
        )
        self.reflections: List[Dict] = self._load_json(self.reflections_file, [])
        
        # Current session tracking
        self.current_session_start = None
        self.current_session_messages = []
        self.current_session_tools = []
        self.current_session_files = []
        self.current_session_commands = []
    
    def _load_json(self, filepath: Path, default: Any) -> Any:
        """Load JSON from file or return default"""
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return default
        return default
    
    def _save_json(self, filepath: Path, data: Any):
        """Save data to JSON file"""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
    
    def start_session(self):
        """Begin a new session"""
        self.current_session_start = datetime.now()
        self.current_session_messages = []
        self.current_session_tools = []
        self.current_session_files = []
        self.current_session_commands = []
        return self.current_session_start
    
    def track_message(self, role: str, content: str):
        """Track a message in the current session"""
        self.current_session_messages.append({
            "role": role,
            "content": content[:500],  # Truncate for storage
            "timestamp": datetime.now().isoformat()
        })
    
    def track_tool_use(self, tool_name: str, arguments: Dict, success: bool):
        """Track tool usage"""
        self.current_session_tools.append({
            "tool": tool_name,
            "arguments": {k: str(v)[:100] for k, v in arguments.items()},
            "success": success,
            "timestamp": datetime.now().isoformat()
        })
    
    def track_file_modified(self, filepath: str):
        """Track file modifications"""
        if filepath not in self.current_session_files:
            self.current_session_files.append(filepath)
    
    def track_command(self, command: str, success: bool):
        """Track command execution"""
        self.current_session_commands.append({
            "command": command,
            "success": success,
            "timestamp": datetime.now().isoformat()
        })
    
    def end_session(self, summary: str = "", key_decisions: List[str] = None):
        """End the current session and save it"""
        if not self.current_session_start:
            return None
        
        end_time = datetime.now()
        duration = (end_time - self.current_session_start).total_seconds()
        
        # Calculate success rate
        tool_successes = sum(1 for t in self.current_session_tools if t.get("success", True))
        total_tools = len(self.current_session_tools) or 1
        success_rate = tool_successes / total_tools
        
        # Create session record
        session = Session(
            id=datetime.now().strftime("%Y%m%d_%H%M%S"),
            timestamp=self.current_session_start.isoformat(),
            duration_seconds=int(duration),
            user_messages=sum(1 for m in self.current_session_messages if m["role"] == "user"),
            agent_responses=sum(1 for m in self.current_session_messages if m["role"] == "assistant"),
            tools_used=list(set(t.get("tool", "unknown") for t in self.current_session_tools)),
            files_modified=self.current_session_files.copy(),
            commands_run=[c["command"] for c in self.current_session_commands],
            success_rate=success_rate,
            summary=summary,
            key_decisions=key_decisions or []
        )
        
        self.sessions.append(session)
        self._save_json(self.sessions_file, [asdict(s) for s in self.sessions])
        
        # Reset current session
        self.current_session_start = None
        self.current_session_messages = []
        
        return session
    
    def add_learning(self, category: str, pattern: str, example: str, confidence: float = 0.5):
        """Add or reinforce a learned pattern"""
        # Check if similar learning exists
        for learning in self.learnings:
            if learning.pattern == pattern:
                learning.times_seen += 1
                learning.confidence = min(1.0, learning.confidence + 0.1)
                learning.last_reinforced = datetime.now().isoformat()
                self._save_learnings()
                return learning
        
        # Create new learning
        learning = Learning(
            id=datetime.now().strftime("%Y%m%d_%H%M%S"),
            timestamp=datetime.now().isoformat(),
            category=category,
            pattern=pattern,
            example=example,
            confidence=confidence,
            times_seen=1,
            last_reinforced=datetime.now().isoformat()
        )
        
        self.learnings.append(learning)
        self._save_learnings()
        return learning
    
    def _save_learnings(self):
        """Save learnings to file"""
        self._save_json(self.learnings_file, [asdict(l) for l in self.learnings])
    
    def get_learnings(self, category: str = None) -> List[Learning]:
        """Get learned patterns, optionally filtered by category"""
        if category:
            return [l for l in self.learnings if l.category == category]
        return self.learnings
    
    def get_context(self) -> Optional[ProjectContext]:
        """Get project context"""
        return self.context
    
    def save_context(self, context: ProjectContext):
        """Save project context"""
        self.context = context
        self._save_json(self.context_file, asdict(context))
    
    def add_reflection(self, reflection: Dict):
        """Add a self-reflection entry"""
        reflection["timestamp"] = datetime.now().isoformat()
        self.reflections.append(reflection)
        self._save_json(self.reflections_file, self.reflections)
    
    def get_reflections(self, limit: int = 10) -> List[Dict]:
        """Get recent reflections"""
        return self.reflections[-limit:]
    
    def get_summary(self) -> Dict:
        """Get a summary of all memory data"""
        return {
            "total_sessions": len(self.sessions),
            "total_learnings": len(self.learnings),
            "total_reflections": len(self.reflections),
            "has_context": self.context is not None,
            "recent_sessions": [asdict(s) for s in self.sessions[-5:]],
            "top_learnings": sorted(self.learnings, key=lambda l: l.confidence, reverse=True)[:10]
        }
    
    def search_sessions(self, query: str) -> List[Session]:
        """Search sessions by content"""
        results = []
        query_lower = query.lower()
        
        for session in self.sessions:
            # Search in summary, decisions, files, commands
            searchable = (
                session.summary.lower() + 
                " ".join(session.key_decisions).lower() +
                " ".join(session.files_modified).lower() +
                " ".join(session.commands_run).lower()
            )
            
            if query_lower in searchable:
                results.append(session)
        
        return results
    
    def export_memory(self, filepath: str = None):
        """Export all memory to a single file"""
        if not filepath:
            filepath = self.memory_dir / "export.json"
        
        export_data = {
            "exported_at": datetime.now().isoformat(),
            "project_path": str(self.project_path),
            "sessions": [asdict(s) for s in self.sessions],
            "learnings": [asdict(l) for l in self.learnings],
            "context": asdict(self.context) if self.context else None,
            "reflections": self.reflections
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        return filepath
