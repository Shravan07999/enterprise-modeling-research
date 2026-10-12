from pathlib import Path

from semantic_input_builder.config import AppConfig, PromptMode
from semantic_input_builder.llm_client import BaseLLMClient
from semantic_input_builder.pipeline import run_pipeline
from semantic_input_builder.schemas import Component, Relationship, SemanticExtraction


class MockLLMClient(BaseLLMClient):
    def __init__(self, extraction: SemanticExtraction) -> None:
        self.extraction = extraction

    def generate_structured(self, messages, response_model):
        return self.extraction


def test_pipeline_end_to_end(tmp_path: Path) -> None:
    prompts_dir = Path(__file__).parent.parent / "prompts"

    scenario_file = tmp_path / "controlled_scenario_business_process_phase1.txt"
    scenario_file.write_text(
        "During target setting, customer surveys are collected.", encoding="utf-8"
    )

    mock_data = SemanticExtraction(
        model_type="business_process",
        components=[
            Component(name="Target Setting", type="Business Process"),
            Component(name="Customer Survey", type="Information Set"),
        ],
        relationships=[
            Relationship(
                source="Customer Survey",
                type="is input to",
                target="Target Setting",
            )
        ],
    )

    config = AppConfig(
        prompts_dir=prompts_dir,
        output_dir=tmp_path / "output",
        llm_api_key="mock-key",
    )

    final_text = run_pipeline(
        scenario_path=scenario_file,
        prompt_mode=PromptMode.SEMANTIC_ONLY,
        save_extraction=True,
        llm_client=MockLLMClient(mock_data),
        config=config,
    )

    assert "Business Process Model" in final_text
    assert "target setting, customer surveys" in final_text
    assert "Customer Survey is input to Target Setting" in final_text
    assert "You are a model generator" in final_text
    assert "============" not in final_text

    output_dir = config.output_dir
    assert (output_dir / "extractions" / "controlled_scenario_business_process_phase1.json").is_file()
    assert (output_dir / "final_inputs" / "controlled_scenario_business_process_phase1.txt").is_file()
