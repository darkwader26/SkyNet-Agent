"""Multi-model router — sends each task to the best model."""

import re
from typing import Optional

from config import MODEL_ROUTER


class TaskRouter:
    """Routes tasks to the best model based on task type."""
    
    @staticmethod
    def classify(prompt: str) -> str:
        """Classify a prompt into a task category."""
        
        if re.search(r"(write|implement|generate|create)\s+(a\s+)?(function|class|script|program|code|api|endpoint)", prompt.lower()):
            return "code"
        if re.search(r"(why|explain|analyze|compare|debug|how\s+does)", prompt.lower()):
            return "reasoning"
        if re.search(r"(write\s+(a\s+)?(story|poem|email|post|tweet)|brainstorm|create\s+(a\s+)?(title|tagline|slogan))", prompt.lower()):
            return "creative"
        if re.search(r"(what\s+is|who\s+is|define|summarize|list|tell\s+me\s+about)", prompt.lower()):
            return "fast"
        if "image" in prompt.lower() or "[image" in prompt.lower():
            return "vision"
        return "reasoning"
    
    @staticmethod
    def get_model(prompt: str) -> str:
        """Get the best model for a given prompt."""
        category = TaskRouter.classify(prompt)
        return MODEL_ROUTER.get(category, MODEL_ROUTER["reasoning"])
    
    @staticmethod
    def status() -> dict:
        return {"routes": MODEL_ROUTER, "default": "reasoning"}
