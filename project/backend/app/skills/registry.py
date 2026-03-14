from __future__ import annotations

import threading

from app.skills.base import Skill


class SkillRegistry:
    """Singleton registry for all available skills."""

    _instance: SkillRegistry | None = None
    _lock = threading.Lock()

    def __new__(cls) -> SkillRegistry:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._skills: dict[str, Skill] = {}
        return cls._instance

    def register(self, skill: Skill) -> None:
        self._skills[skill.name] = skill

    def get_skill(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def list_skills(self) -> list[Skill]:
        return list(self._skills.values())

    def get_skill_descriptions(self) -> list[dict]:
        return [
            {
                "name": s.name,
                "description": s.description,
                "trigger_phrases": s.trigger_phrases,
            }
            for s in self._skills.values()
        ]
