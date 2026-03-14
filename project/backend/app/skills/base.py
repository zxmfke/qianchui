from abc import ABC, abstractmethod


class Skill(ABC):
    """Base class for all Skills in the 千锤 system."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        ...

    @property
    @abstractmethod
    def trigger_phrases(self) -> list[str]:
        ...

    @abstractmethod
    async def execute(self, user_input: str, context: dict) -> dict:
        """Execute skill and return structured result.

        Returns:
            {
                "text": str,           # AI的文字回答
                "cards": list[dict],   # 结构化卡片
                "suggested_actions": list[dict]  # 建议的后续操作
            }
        """
        pass
