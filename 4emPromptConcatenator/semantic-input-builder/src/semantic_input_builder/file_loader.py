from pathlib import Path
from semantic_input_builder.config import PromptMode


class FileLoadError(Exception):
    pass


def load_text_file(path: Path | str) -> str:
    target = Path(path)
    if not target.is_file():
        raise FileNotFoundError(f"File not found: {target}")
    return target.read_text(encoding="utf-8")


def load_model_preprompt(prompts_dir: Path | str, model_type: str) -> str:
    return load_text_file(Path(prompts_dir) / model_type / "preprompt.txt")


def load_model_prompt(prompts_dir: Path | str, model_type: str) -> str:
    model_dir = Path(prompts_dir) / model_type
    prompt_file = model_dir / "prompt_original.txt"
    if not prompt_file.exists():
        prompt_file = model_dir / "prompt.txt"
    return load_text_file(prompt_file)


def load_model_semantic_instructions(prompts_dir: Path | str, model_type: str) -> str:
    model_dir = Path(prompts_dir) / model_type
    downstream_file = model_dir / "prompt_for_downstream.txt"
    if not downstream_file.exists():
        downstream_file = model_dir / "semantic_instructions.txt"
    return load_text_file(downstream_file)


def load_prompt_by_mode(prompts_dir: Path | str, model_type: str, mode: PromptMode) -> str:
    if mode == PromptMode.NONE:
        return ""
    if mode == PromptMode.FULL_PROMPT:
        return load_model_prompt(prompts_dir, model_type)
    if mode == PromptMode.SEMANTIC_ONLY:
        return load_model_semantic_instructions(prompts_dir, model_type)
    raise ValueError(f"Unknown prompt mode: {mode}")
