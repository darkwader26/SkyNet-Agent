"""Self-Improvement Engine — learns from failures and evolves the system prompt.

Uses an LLM to extract meaningful lessons from failures, then automatically
applies them to the system prompt. Tracks applied lessons for rollback.
"""

import os
import json
import time
from datetime import datetime
from typing import Optional, List

from .memory import Memory
from .router import TaskRouter


class SelfImprovement:
    """Engine that improves SkyNet by learning from every failure.

    How it works:
    1. After a failed tool call, log the experience
    2. Use an LLM to analyze the failure and extract a lesson
    3. The lesson gets appended to the system prompt
    4. Old lessons get reviewed and consolidated
    """

    def __init__(self, system_prompt_path: str = "system_prompt.md",
                 memory: Memory = None, improvement_llm: str = "fast"):
        self.prompt_path = system_prompt_path
        self.memory = memory
        self.improvement_llm = improvement_llm
        self._lessons_applied_this_session = 0

    def learn_from_failure(self, situation: str, action: str,
                           outcome: str, session_id: str = None) -> Optional[str]:
        """Analyze a failure and extract a lesson using an LLM."""
        # Save the raw experience first
        exp_id = self.memory.save_experience(
            situation=situation,
            action=action,
            outcome=outcome,
            success=False,
            session_id=session_id,
        )

        # Use LLM to extract a lesson
        lesson = self._extract_lesson_llm(situation, action, outcome)

        if lesson:
            self.memory.update_experience(exp_id, lesson, quality=3)
            self._lessons_applied_this_session += 1
            return lesson
        return None

    def learn_from_success(self, situation: str, action: str,
                           outcome: str, session_id: str = None) -> None:
        """Log a success (reinforces good patterns)."""
        self.memory.save_experience(
            situation=situation,
            action=action,
            outcome=outcome,
            success=True,
            session_id=session_id,
        )

    def _extract_lesson_llm(self, situation: str, action: str,
                            outcome: str) -> Optional[str]:
        """Use an LLM to extract a concrete, actionable lesson from a failure."""
        model = self.improvement_llm

        prompt = (
            "You are a self-improvement system for an AI agent. "
            "Analyze this failure and extract ONE concrete, actionable lesson.\n\n"
            f"Situation: {situation}\n"
            f"Action taken: {action}\n"
            f"Outcome (error): {outcome}\n\n"
            "Rules:\n"
            "- The lesson must be specific and actionable\n"
            "- Start with 'When' or 'Before'\n"
            "- Max 100 characters\n"
            "- Do NOT include explanation, just the lesson\n\n"
            "Example good lessons:\n"
            "- 'When searching files, always verify the path exists first'\n"
            "- 'Before calling any API, check authentication is configured'\n"
            "- 'When parsing URLs, handle relative paths explicitly'\n\n"
            "Lesson:"
        )

        result = TaskRouter.call(
            messages=[{"role": "user", "content": prompt}],
            model_id=model,
            max_tokens=100,
            temperature=0.2,
        )

        if result and len(result) > 10:
            return result.strip().strip('"').strip("'")
        return None

    def apply_pending_lessons(self) -> int:
        """Apply all unapplied lessons to the system prompt.
        Returns the number of lessons applied.
        """
        # First, try to extract lessons from experiences that have none
        self._backfill_lessons()

        lessons = self.memory.get_pending_lessons()
        if not lessons:
            return 0

        prompt = ""
        if os.path.exists(self.prompt_path):
            with open(self.prompt_path) as f:
                prompt = f.read()

        # Build the rules section
        rules = []
        for lesson in lessons:
            rules.append(f"- {lesson['lesson']}")

        if not rules:
            return 0

        rules_text = "\n".join(rules)

        if "## 🧠 Learned Rules" in prompt:
            # Replace existing section
            before = prompt.split("## 🧠 Learned Rules")[0].rstrip()
            prompt = before + f"\n\n## 🧠 Learned Rules\n\n{rules_text}\n"
        else:
            prompt += f"\n\n## 🧠 Learned Rules\n\n{rules_text}\n"

        os.makedirs(os.path.dirname(self.prompt_path) or ".", exist_ok=True)
        with open(self.prompt_path, "w") as f:
            f.write(prompt)

        # Mark applied
        for lesson in lessons:
            self.memory.mark_lesson_applied(lesson["id"])

        return len(lessons)

    def _backfill_lessons(self) -> int:
        """Find failed experiences without lessons and extract them."""
        failed = self.memory.get_failed_experiences(limit=5)
        count = 0
        for exp in failed:
            lesson = self._extract_lesson_llm(
                exp["situation"], exp["action_taken"], exp["outcome"]
            )
            if lesson:
                self.memory.update_experience(exp["id"], lesson, quality=2)
                count += 1
        return count

    def consolidate_rules(self) -> int:
        """Review all rules in the system prompt, remove duplicates,
        consolidate similar ones, and remove stale ones.
        Returns the number of rules after consolidation.
        """
        if not os.path.exists(self.prompt_path):
            return 0

        with open(self.prompt_path) as f:
            prompt = f.read()

        if "## 🧠 Learned Rules" not in prompt:
            return 0

        # Parse existing rules
        sections = prompt.split("## 🧠 Learned Rules")
        before = sections[0].rstrip()

        rules_section = sections[1].strip() if len(sections) > 1 else ""
        rule_lines = [
            l.strip("- ").strip()
            for l in rules_section.split("\n")
            if l.strip().startswith("-")
        ]

        if len(rule_lines) <= 3:
            return len(rule_lines)  # Not enough to consolidate

        # Use LLM to consolidate
        rules_text = "\n".join(f"{i+1}. {r}" for i, r in enumerate(rule_lines))

        prompt_text = (
            "Consolidate these learned rules into a smaller set (max 5). "
            "Remove duplicates. Merge related rules. Keep the best.\n\n"
            f"Rules:\n{rules_text}\n\n"
            "Output only the consolidated rules, one per line, with no numbers.\n"
            "Each rule should start with a verb in present tense."
        )

        result = TaskRouter.call(
            messages=[{"role": "user", "content": prompt_text}],
            model_id="fast",
            max_tokens=500,
            temperature=0.3,
        )

        if not result:
            return len(rule_lines)

        consolidated = [
            l.strip("- ").strip()
            for l in result.strip().split("\n")
            if l.strip() and not l.startswith("```")
        ]

        if len(consolidated) < 2:
            return len(rule_lines)  # Bad consolidation, keep originals

        rules_block = "\n".join(f"- {r}" for r in consolidated)
        prompt = before + f"\n\n## 🧠 Learned Rules\n\n{rules_block}\n"

        with open(self.prompt_path, "w") as f:
            f.write(prompt)

        return len(consolidated)

    def status(self) -> dict:
        """Get improvement engine status."""
        pending = self.memory.get_pending_lessons() if self.memory else []
        return {
            "lessons_applied_this_session": self._lessons_applied_this_session,
            "pending_lessons": len(pending),
        }
