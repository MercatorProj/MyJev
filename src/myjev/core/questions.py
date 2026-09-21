from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import ClassVar, TypeAlias

DEFAULT_MODEL = "jev-latest"

from ..utils.json import is_json_content
from .types import JSONContent


def _validate_instructions(instructions: JSONContent | None) -> None:
    if instructions is not None and not is_json_content(instructions):
        raise ValueError("instructions must be a string, JSON object, JSON array, or None")


@dataclass(frozen=True, slots=True, kw_only=True)
class Choice:
    """A question that selects one option from a set of named choices."""

    criteria: Mapping[str, JSONContent | None]
    instructions: JSONContent | None = None

    type: ClassVar[str] = "choice"

    def __post_init__(self) -> None:
        _validate_instructions(self.instructions)
        criteria = dict(self.criteria)
        if any(not isinstance(name, str) or not name for name in criteria):
            raise ValueError("choice option names must be non-empty strings")
        if any(description is not None and not is_json_content(description) for description in criteria.values()):
            raise ValueError("choice descriptions must be JSON content or None")
        object.__setattr__(self, "criteria", criteria)

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "type": self.type,
            "instructions": self.instructions,
            "criteria": dict(self.criteria),
        }
        if self.instructions is None:
            del result["instructions"]
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class Score:
    """A question that rates content against ordered descriptive levels."""

    criteria: Sequence[JSONContent]
    instructions: JSONContent | None = None

    type: ClassVar[str] = "score"

    def __post_init__(self) -> None:
        _validate_instructions(self.instructions)
        if isinstance(self.criteria, (str, bytes)):
            raise ValueError("score criteria must be a sequence of level descriptions")
        criteria = tuple(self.criteria)
        if not criteria:
            raise ValueError("score criteria must contain at least one level")
        if any(not is_json_content(description) for description in criteria):
            raise ValueError("score level descriptions must be JSON content")
        object.__setattr__(self, "criteria", criteria)

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "type": self.type,
            "instructions": self.instructions,
            "criteria": list(self.criteria),
        }
        if self.instructions is None:
            del result["instructions"]
        return result


@dataclass(frozen=True, slots=True, kw_only=True)
class Noul:
    """A yes/no question that produces the probability that the answer is yes."""

    instructions: JSONContent | None = None
    criteria: Mapping[str, JSONContent | None] | None = None

    type: ClassVar[str] = "noul"

    def __post_init__(self) -> None:
        _validate_instructions(self.instructions)
        if self.criteria is None:
            return
        criteria = dict(self.criteria)
        if not set(criteria) <= {"true", "false"}:
            raise ValueError('noul criteria may only contain "true" and "false"')
        if any(description is not None and not is_json_content(description) for description in criteria.values()):
            raise ValueError("noul descriptions must be JSON content or None")
        object.__setattr__(self, "criteria", criteria)

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {"type": self.type}
        if self.instructions is not None:
            result["instructions"] = self.instructions
        if self.criteria is not None:
            result["criteria"] = dict(self.criteria)
        return result


Question: TypeAlias = Choice | Score | Noul | Mapping[str, object]
QuestionInput: TypeAlias = Question
Questions: TypeAlias = Mapping[str, QuestionInput]


def validate_question_input(value: object) -> object:
    """Validate question shape without converting or copying raw dictionaries."""

    if isinstance(value, (Choice, Score, Noul)):
        return value
    if not isinstance(value, dict) or not isinstance(value.get("type"), str) or not value["type"]:
        raise ValueError("each question must be a question object or a dict with a nonempty string type")
    if value["type"] in ("choice", "score") and "criteria" not in value:
        raise ValueError(f'{value["type"]} questions require criteria')
    if value["type"] == "score" and not value["criteria"]:
        raise ValueError("score questions require at least one criterion")
    return value


def parse_question(value: object) -> Question:
    """Parse a JSON-shaped question while preserving typed question objects."""

    if isinstance(value, (Choice, Score, Noul)):
        return value
    if not isinstance(value, Mapping):
        raise ValueError("each question must be a JSON object")

    question_type = value.get("type")
    instructions = value.get("instructions")
    if question_type == "choice":
        criteria = value.get("criteria")
        if not isinstance(criteria, Mapping):
            raise ValueError("choice criteria must be a JSON object")
        return Choice(
            instructions=instructions,  # type: ignore[arg-type]
            criteria=criteria,  # type: ignore[arg-type]
        )
    if question_type == "score":
        if "criteria" not in value:
            raise ValueError("score criteria is required")
        return Score(
            instructions=instructions,  # type: ignore[arg-type]
            criteria=value["criteria"],  # type: ignore[arg-type]
        )
    if question_type == "noul":
        criteria = value.get("criteria")
        if criteria is not None and not isinstance(criteria, Mapping):
            raise ValueError("noul criteria must be a JSON object")
        return Noul(
            instructions=instructions,  # type: ignore[arg-type]
            criteria=criteria,  # type: ignore[arg-type]
        )
    raise ValueError("question type must be choice, score, or noul")
