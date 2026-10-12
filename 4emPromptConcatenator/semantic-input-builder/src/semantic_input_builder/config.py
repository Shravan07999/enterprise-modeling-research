from dataclasses import dataclass, field
from enum import Enum
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class PromptMode(str, Enum):
    SEMANTIC_ONLY = "semantic_only"
    FULL_PROMPT = "full_prompt"
    NONE = "none"


@dataclass
class AppConfig:
    llm_api_key: str | None = None
    llm_base_url: str = field(default_factory=lambda: os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "gpt-4o-mini"))
    prompt_mode: PromptMode = field(default_factory=lambda: PromptMode(os.getenv("DEFAULT_PROMPT_MODE", "semantic_only")))
    prompts_dir: Path = field(default_factory=lambda: Path(os.getenv("PROMPTS_DIR", "prompts")))
    output_dir: Path = field(default_factory=lambda: Path(os.getenv("OUTPUT_DIR", "output")))
    scenarios_dir: Path = field(default_factory=lambda: Path(os.getenv("SCENARIOS_DIR", "scenarios")))

    def __post_init__(self) -> None:
        if self.llm_api_key is None:
            self.llm_api_key = os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
        if isinstance(self.prompt_mode, str) and not isinstance(self.prompt_mode, PromptMode):
            self.prompt_mode = PromptMode(self.prompt_mode)
        if isinstance(self.prompts_dir, str):
            self.prompts_dir = Path(self.prompts_dir)
        if isinstance(self.output_dir, str):
            self.output_dir = Path(self.output_dir)
        if isinstance(self.scenarios_dir, str):
            self.scenarios_dir = Path(self.scenarios_dir)


def get_config() -> AppConfig:
    return AppConfig()
