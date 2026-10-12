from abc import ABC, abstractmethod
import json

from openai import OpenAI
from pydantic import BaseModel

from semantic_input_builder.config import AppConfig


class BaseLLMClient(ABC):
    @abstractmethod
    def generate_structured(
        self,
        messages: list[dict[str, str]],
        response_model: type[BaseModel],
    ) -> BaseModel: ...


class OpenAILLMClient(BaseLLMClient):
    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or AppConfig()
        if not self.config.llm_api_key:
            raise ValueError(
                "LLM_API_KEY environment variable is not set. "
                "Please configure LLM_API_KEY in your .env or environment."
            )
        self.client = OpenAI(
            api_key=self.config.llm_api_key,
            base_url=self.config.llm_base_url,
        )

    def generate_structured(
        self,
        messages: list[dict[str, str]],
        response_model: type[BaseModel],
    ) -> BaseModel:
        try:
            completion = self.client.beta.chat.completions.parse(
                model=self.config.llm_model,
                messages=messages,  # type: ignore[arg-type]
                response_format=response_model,
                temperature=0.0,
            )
            parsed = completion.choices[0].message.parsed
            if parsed is not None:
                return parsed
        except Exception:
            pass

        schema_prompt = json.dumps(response_model.model_json_schema(), indent=2)
        fallback_messages = [dict(m) for m in messages]
        fallback_messages[0]["content"] += (
            f"\n\nRespond with valid JSON adhering to this schema:\n{schema_prompt}"
        )

        raw = self.client.chat.completions.create(  # type: ignore[call-overload]
            model=self.config.llm_model,
            messages=fallback_messages,  # type: ignore[arg-type]
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        content = raw.choices[0].message.content or "{}"
        return response_model.model_validate_json(content)
