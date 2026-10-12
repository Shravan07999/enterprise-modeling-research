"""LLM client wrapper providing retry handling and telemetry capture."""

import re
import time
import os
import json

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

_API_TIMEOUT_SECONDS = 90
_MAX_RETRIES = 2


class QRewEngine:

    def __init__(self, model_name: str = None):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model_name = model_name or os.getenv(
            "OPENAI_MODEL_NAME", "gpt-4o"
        )

    @staticmethod
    def _extract_tokens(usage) -> tuple[int, int]:
        if usage is None:
            return -1, -1
        pt = usage.prompt_tokens
        ct = usage.completion_tokens
        return (pt if pt is not None else -1, ct if ct is not None else -1)

    @staticmethod
    def _strip_markdown_fences(text: str) -> str:
        text = text.strip()
        text = re.sub(r"^```\w*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        return text.strip()

    def _call_openai(self, prompt: str) -> tuple:
        last_exc = None
        for attempt in range(1 + _MAX_RETRIES):
            try:
                start = time.perf_counter()
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2,
                    timeout=_API_TIMEOUT_SECONDS,
                )
                latency = time.perf_counter() - start
                prompt_tokens, completion_tokens = self._extract_tokens(
                    response.usage
                )
                text = response.choices[0].message.content
                if text is None:
                    raise RuntimeError(
                        "OpenAI response was blocked: no text returned"
                    )
                return text.strip(), latency, prompt_tokens, completion_tokens
            except Exception as e:
                last_exc = e
                if attempt < _MAX_RETRIES:
                    wait = 2 ** attempt
                    time.sleep(wait)
        raise last_exc

    def generate_canonical_model(self, rewritten_query: str, framework: str) -> tuple[dict, dict]:
        """Generate canonical semantic model with retry."""
        from config import STAGE_2B_TEMPLATE_4EM, STAGE_2B_TEMPLATE_BPMN

        if framework == "4EM":
            prompt = STAGE_2B_TEMPLATE_4EM.format(rewritten_query=rewritten_query)
        elif framework == "BPMN":
            prompt = STAGE_2B_TEMPLATE_BPMN.format(rewritten_query=rewritten_query)
        else:
            raise ValueError(f"Canonical model generation not supported for framework: {framework}")

        last_exc = None
        for attempt in range(1 + _MAX_RETRIES):
            try:
                text, latency, pt, ct = self._call_openai(prompt)
                clean_text = self._strip_markdown_fences(text)
                model = json.loads(clean_text)

                metrics = {
                    "stage_2b_latency_seconds": latency,
                    "stage_2b_prompt_tokens": pt,
                    "stage_2b_completion_tokens": ct,
                }
                return model, metrics

            except (json.JSONDecodeError, ValueError) as e:
                last_exc = e
                if attempt < _MAX_RETRIES:
                    prompt += f"\n\nNote: Previous response failed parsing ({e}). Return strictly valid JSON matching the schema."
                    time.sleep(2 ** attempt)
                else:
                    raise

        raise last_exc
