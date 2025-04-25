from abc import ABC, abstractmethod

class LLMInterface(ABC):
    @abstractmethod
    async def generate_code(self, prompt: str) -> str:
        pass

    @abstractmethod
    async def review_code(self, code: str) -> str:
        pass