"""Self-Improvement Engine — learns from mistakes and rewrites the system prompt."""

import os
import json
from datetime import datetime
from typing import Optional

from memory import Memory


class SelfImprovement:
    """Engine that improves the agent by learning from experience."""
    
    def __init__(self, system_prompt_path: str = "system_prompt.md",
                 memory: Memory = None):
        self.prompt_path = system_prompt_path
        self.memory = memory or Memory()
    
    def learn_from_outcome(self, situation: str, action: str,
                           outcome: str, success: bool) -> Optional[str]:
        """Analyze an outcome and extract a lesson."""
        if success:
            return None
        
        lesson = self._extract_lesson(situation, action, outcome)
        if lesson:
            self.memory.save_experience(situation, action, outcome, lesson)
            return lesson
        return None
    
    def _extract_lesson(self, situation: str, action: str,
                        outcome: str) -> Optional[str]:
        """Extract a rule from a failure using pattern matching."""
        outcome_lower = outcome.lower()
        
        if "error" in outcome_lower or "exception" in outcome_lower:
            return f"When handling: {situation}, always validate inputs before acting."
        if "not found" in outcome_lower or "missing" in outcome_lower:
            return f"Before {action}, check prerequisites exist."
        if "timeout" in outcome_lower or "timed out" in outcome_lower:
            return f"Set appropriate timeouts for {action}."
        return None
    
    def apply_lessons(self) -> int:
        """Scan unapplied lessons and add them to the system prompt."""
        lessons = self.memory.get_lessons()
        if not lessons:
            return 0
        
        prompt = ""
        if os.path.exists(self.prompt_path):
            with open(self.prompt_path, "r") as f:
                prompt = f.read()
        
        rules_section = "\n\n## 🧠 Learned Rules\n\n"
        for lesson in lessons:
            rules_section += f"- {lesson['lesson']}\n"
        
        if "## 🧠 Learned Rules" in prompt:
            prompt = prompt.split("## 🧠 Learned Rules")[0].rstrip()
        
        prompt += rules_section
        
        with open(self.prompt_path, "w") as f:
            f.write(prompt)
        
        for lesson in lessons:
            self.memory.mark_lesson_applied(lesson['id'])
        
        return len(lessons)
    
    def review_system_prompt(self) -> dict:
        """Analyze the current system prompt."""
        if not os.path.exists(self.prompt_path):
            return {"status": "no_prompt"}
        
        with open(self.prompt_path, "r") as f:
            content = f.read()
        
        return {
            "status": "ok",
            "lines": content.count("\n") + 1,
            "words": len(content.split()),
            "has_rules": "Learned Rules" in content,
        }
