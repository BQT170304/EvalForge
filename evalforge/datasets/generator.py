"""Synthetic test dataset generator using LiteLLM."""

import json
from typing import Any

import structlog

from evalforge.utils.llm_client import get_llm_client

logger = structlog.get_logger(__name__)


class SyntheticDataGenerator:
    """Generates synthetic golden test cases grounded in user context, seed examples, or domain criteria."""

    def __init__(self, model: str | None = None) -> None:
        self.model = model

    async def generate_test_cases(
        self,
        domain_description: str,
        num_samples: int = 5,
        context_docs: list[str] | None = None,
        seed_examples: list[dict[str, str]] | None = None,
        difficulty_mix: dict[str, float] | None = None,
    ) -> list[dict[str, Any]]:
        """Generates synthetic dataset test cases with inputs, expected outputs, and metadata.

        Args:
            domain_description: Overview of the target application / AI system domain.
            num_samples: Number of synthetic test cases to generate.
            context_docs: Optional documentation chunks to ground questions.
            seed_examples: Optional few-shot seed test cases.
            difficulty_mix: Optional distribution (e.g. {"easy": 0.3, "medium": 0.5, "hard": 0.2}).

        Returns:
            List of generated test case dictionaries.
        """
        llm = get_llm_client(self.model)

        context_str = ""
        if context_docs:
            context_str = "\nRelevant Knowledge Context:\n" + "\n---\n".join(context_docs[:5])

        seeds_str = ""
        if seed_examples:
            seeds_str = "\nSeed Examples:\n" + json.dumps(seed_examples, indent=2)

        prompt = f"""You are a senior AI Evaluation Architect creating a robust evaluation dataset for a production AI system.

Target Domain / System Description:
{domain_description}
{context_str}
{seeds_str}

Generate {num_samples} realistic, challenging, and diverse evaluation test cases.
Include a mix of:
- Standard user queries
- Complex multi-step reasoning questions
- Edge cases / boundary conditions (e.g., incomplete data, ambiguous prompts, adversarial attempts)

Respond ONLY with valid JSON in this exact structure:
{{
  "test_cases": [
    {{
      "input": "<user query or task instruction>",
      "expected_output": "<ideal high-quality ground truth answer>",
      "context": ["<supporting context chunk 1 if applicable>"],
      "metadata": {{
        "category": "<domain sub-category>",
        "difficulty": "<easy|medium|hard|adversarial>",
        "persona": "<user persona description>"
      }}
    }}
  ]
}}"""

        try:
            response_text, cost_usd, _ = await llm.complete(
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=4096,
            )

            parsed = json.loads(response_text)
            raw_cases = parsed.get("test_cases", [])
            cases: list[dict[str, Any]] = [dict(c) for c in raw_cases if isinstance(c, dict)]
            logger.info("synthetic_cases_generated", count=len(cases), cost_usd=cost_usd)
            return cases

        except Exception as e:
            logger.error("synthetic_generation_failed", error=str(e))
            raise RuntimeError(f"Synthetic test data generation failed: {e}") from e
