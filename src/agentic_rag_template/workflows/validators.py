"""Reusable validators for workflow outputs."""

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Protocol


@dataclass(frozen=True)
class ValidationContext:
    initial_input: Dict[str, Any] = field(default_factory=dict)
    configuration: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ValidationResult:
    validator_id: str
    valid: bool
    severity: str = "error"
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "validator_id": self.validator_id,
            "valid": self.valid,
            "severity": self.severity,
            "errors": self.errors,
            "warnings": self.warnings,
            "metrics": self.metrics,
        }


class WorkflowValidator(Protocol):
    validator_id: str

    def validate(self, value: Any, context: ValidationContext) -> ValidationResult:
        """Validate a workflow value."""


class JsonParseValidator:
    validator_id = "json_parse"

    def validate(self, value: Any, context: ValidationContext) -> ValidationResult:
        if isinstance(value, (dict, list)):
            return ValidationResult(self.validator_id, True)
        try:
            json.loads(str(value))
        except json.JSONDecodeError as error:
            return ValidationResult(self.validator_id, False, errors=[str(error)])
        return ValidationResult(self.validator_id, True)


class RequiredFieldsValidator:
    validator_id = "required_fields"

    def validate(self, value: Any, context: ValidationContext) -> ValidationResult:
        required = context.configuration.get("required", [])
        if not isinstance(value, dict):
            return ValidationResult(self.validator_id, False, errors=["value must be an object"])
        missing = [field for field in required if field not in value]
        return ValidationResult(
            self.validator_id,
            not missing,
            errors=[f"missing required field: {field}" for field in missing],
            metrics={"missing_count": len(missing)},
        )


class NoAdditionalPropertiesValidator:
    validator_id = "no_additional_properties"

    def validate(self, value: Any, context: ValidationContext) -> ValidationResult:
        allowed = set(context.configuration.get("allowed", []))
        if not isinstance(value, dict) or not allowed:
            return ValidationResult(self.validator_id, True)
        additional = sorted(set(value.keys()) - allowed)
        return ValidationResult(
            self.validator_id,
            not additional,
            errors=[f"additional field is not allowed: {field}" for field in additional],
            metrics={"additional_count": len(additional)},
        )


class UniqueIdsValidator:
    validator_id = "unique_ids"

    def validate(self, value: Any, context: ValidationContext) -> ValidationResult:
        path = context.configuration.get("path", "")
        items = _get_path(value, path) if path else value
        if not isinstance(items, list):
            return ValidationResult(self.validator_id, True)
        ids = [item.get("id") for item in items if isinstance(item, dict) and item.get("id")]
        duplicates = sorted({item_id for item_id in ids if ids.count(item_id) > 1})
        return ValidationResult(
            self.validator_id,
            not duplicates,
            errors=[f"duplicate id: {item_id}" for item_id in duplicates],
            metrics={"duplicate_count": len(duplicates)},
        )


class JsonSchemaValidator:
    validator_id = "json_schema"

    def validate(self, value: Any, context: ValidationContext) -> ValidationResult:
        schema = context.configuration.get("schema", {})
        if not schema:
            return ValidationResult(self.validator_id, True)
        errors = _validate_schema(value, schema)
        return ValidationResult(self.validator_id, not errors, errors=errors)


class ScopeEvidenceValidator:
    validator_id = "scope_evidence"

    def validate(self, value: Any, context: ValidationContext) -> ValidationResult:
        requirement_analysis = _get_path(
            context.initial_input,
            str(context.configuration.get("requirement_analysis_path", "requirement_analysis")),
        )
        if not isinstance(requirement_analysis, dict):
            return ValidationResult(self.validator_id, False, errors=["requirement_analysis must be available"])

        ignored_keys = set(
            context.configuration.get(
                "ignored_keys",
                [
                    "assumptions",
                    "explicitly_excluded",
                    "explicitly_excluded_terms",
                    "non_goals",
                    "not_evidenced",
                    "open_questions",
                    "out_of_scope",
                    "requirement_trace",
                ],
            )
        )
        output_text = _normalize_for_search(" ".join(_flatten_text(value, ignored_keys=ignored_keys)))
        positive_evidence = _normalize_for_search(
            " ".join(
                _flatten_text(
                    [
                        requirement_analysis.get("input_summary"),
                        requirement_analysis.get("in_scope"),
                        requirement_analysis.get("core_facts"),
                    ]
                )
            )
        )
        forbidden_text = _normalize_for_search(
            " ".join(
                _flatten_text(
                    [
                        requirement_analysis.get("out_of_scope"),
                        requirement_analysis.get("not_evidenced"),
                        requirement_analysis.get("explicitly_excluded"),
                        requirement_analysis.get("explicitly_excluded_terms"),
                        requirement_analysis.get("not_requested"),
                    ]
                )
            )
        )
        extracted_forbidden_terms = [
            term
            for term in _flatten_text(
                [
                    requirement_analysis.get("out_of_scope"),
                    requirement_analysis.get("not_evidenced"),
                    requirement_analysis.get("explicitly_excluded"),
                    requirement_analysis.get("explicitly_excluded_terms"),
                    requirement_analysis.get("not_requested"),
                ]
            )
            if _is_searchable_term(term)
        ]
        watched_terms = [
            str(term)
            for term in context.configuration.get("watched_terms", [])
            if str(term).strip()
        ]

        violations = []
        for term in _dedupe_terms(extracted_forbidden_terms + watched_terms):
            normalized = _normalize_for_search(term)
            if normalized not in output_text:
                continue
            is_explicitly_forbidden = normalized in forbidden_text
            is_not_evidenced = normalized not in positive_evidence
            if is_explicitly_forbidden or is_not_evidenced:
                violations.append(term)

        return ValidationResult(
            self.validator_id,
            not violations,
            errors=[f"scope term is not supported by requirements: {term}" for term in violations],
            metrics={
                "violation_count": len(violations),
                "checked_term_count": len(_dedupe_terms(extracted_forbidden_terms + watched_terms)),
            },
        )


class ForbiddenTermsValidator:
    validator_id = "forbidden_terms"

    def validate(self, value: Any, context: ValidationContext) -> ValidationResult:
        output_text = _normalize_for_search(
            " ".join(_flatten_text(value, ignored_keys=context.configuration.get("ignored_keys", [])))
        )
        terms = _dedupe_terms(
            _configured_required_terms({"required_terms": context.configuration.get("terms", [])})
            + _terms_from_paths(context.initial_input, context.configuration.get("term_source_paths", []))
        )
        violations = [
            term
            for term in terms
            if _normalize_for_search(term) in output_text
        ]
        return ValidationResult(
            self.validator_id,
            not violations,
            errors=[f"forbidden term is present: {term}" for term in violations],
            metrics={"checked_term_count": len(terms), "violation_count": len(violations)},
        )


class EvidenceRequiredValidator:
    validator_id = "evidence_required"

    def validate(self, value: Any, context: ValidationContext) -> ValidationResult:
        evidence = _evidence_terms(context.initial_input, context.configuration)
        if not evidence:
            return ValidationResult(self.validator_id, False, errors=["no evidence terms configured or available"])

        configured_terms = _configured_required_terms({"required_terms": context.configuration.get("checked_terms", [])})
        output_terms = [
            term
            for term in configured_terms
            if _normalize_for_search(term) in _normalize_for_search(" ".join(_flatten_text(value)))
        ]
        if not configured_terms:
            output_terms = _candidate_feature_terms(value, context.configuration)

        unsupported = [
            term
            for term in output_terms
            if not _has_evidence(term, evidence)
        ]
        return ValidationResult(
            self.validator_id,
            not unsupported,
            errors=[f"term has no supporting evidence: {term}" for term in unsupported],
            metrics={"checked_term_count": len(output_terms), "unsupported_count": len(unsupported)},
        )


class NumericPreservationValidator:
    validator_id = "numeric_preservation"

    def validate(self, value: Any, context: ValidationContext) -> ValidationResult:
        source = _get_path(context.initial_input, str(context.configuration.get("source_path", "requirement_analysis")))
        source_numbers = _extract_numbers(" ".join(_flatten_text(source)))
        if not source_numbers:
            return ValidationResult(self.validator_id, True, metrics={"checked_number_count": 0})

        output_numbers = set(_extract_numbers(" ".join(_flatten_text(value))))
        ignored = set(str(item) for item in context.configuration.get("ignore_numbers", []))
        required_numbers = [number for number in source_numbers if number not in ignored]
        missing = [number for number in required_numbers if number not in output_numbers]

        return ValidationResult(
            self.validator_id,
            not missing,
            errors=[f"numeric requirement is missing from output: {number}" for number in missing],
            metrics={
                "checked_number_count": len(required_numbers),
                "missing_number_count": len(missing),
            },
        )


class ExplicitTestCountValidator:
    validator_id = "explicit_test_count"

    def validate(self, value: Any, context: ValidationContext) -> ValidationResult:
        source = _get_path(
            context.initial_input,
            str(context.configuration.get("test_requirements_path", "requirement_analysis.test_requirements")),
        )
        required_count = int(context.configuration.get("min_count", 0) or 0)
        source_items = _list_items(source)
        if source_items:
            required_count = max(required_count, len(source_items))

        output_items = _get_path(value, str(context.configuration.get("output_path", "test_requirements")))
        if output_items is None:
            output_items = _get_path(value, "architecture_sheet.test_requirements")
        output_count = len(_list_items(output_items))

        errors = []
        if output_count < required_count:
            errors.append(f"expected at least {required_count} explicit test requirement(s), found {output_count}")

        return ValidationResult(
            self.validator_id,
            not errors,
            errors=errors,
            metrics={"required_count": required_count, "output_count": output_count},
        )


class TestRequirementCoverageValidator:
    validator_id = "test_requirement_coverage"

    def validate(self, value: Any, context: ValidationContext) -> ValidationResult:
        requirement_analysis = _get_path(
            context.initial_input,
            str(context.configuration.get("requirement_analysis_path", "requirement_analysis")),
        )
        if not isinstance(requirement_analysis, dict):
            return ValidationResult(self.validator_id, False, errors=["requirement_analysis must be available"])

        output_text = _normalize_for_search(" ".join(_flatten_text(value)))
        required_terms = _dedupe_terms(
            _configured_required_terms(context.configuration)
            + _test_requirement_terms(requirement_analysis.get("test_requirements"))
            + _coverage_terms(requirement_analysis)
        )
        missing = [
            term
            for term in required_terms
            if _normalize_for_search(term) not in output_text
        ]

        return ValidationResult(
            self.validator_id,
            not missing,
            errors=[f"test requirement is missing from output: {term}" for term in missing],
            metrics={
                "checked_requirement_count": len(required_terms),
                "missing_requirement_count": len(missing),
            },
        )


class CrossFieldConsistencyValidator:
    validator_id = "cross_field_consistency"

    def validate(self, value: Any, context: ValidationContext) -> ValidationResult:
        rules = context.configuration.get("rules", [])
        if not isinstance(rules, list):
            return ValidationResult(self.validator_id, False, errors=["rules must be a list"])

        errors = []
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            source_path = str(rule.get("source_path", ""))
            target_path = str(rule.get("target_path", ""))
            if not source_path or not target_path:
                continue
            source_value = _get_path(value, source_path)
            target_value = _get_path(value, target_path)
            source_terms = _selected_terms(source_value, rule)
            target_text = _normalize_for_search(" ".join(_flatten_text(target_value)))
            missing = [
                term
                for term in source_terms
                if _normalize_for_search(term) not in target_text
            ]
            errors.extend(
                f"{target_path} is missing term from {source_path}: {term}"
                for term in missing
            )

        return ValidationResult(
            self.validator_id,
            not errors,
            errors=errors,
            metrics={"rule_count": len(rules), "missing_count": len(errors)},
        )


class ValidatorRegistry:
    def __init__(self) -> None:
        self._validators: Dict[str, WorkflowValidator] = {}

    def register(self, validator: WorkflowValidator) -> None:
        self._validators[validator.validator_id] = validator

    def get(self, validator_id: str) -> WorkflowValidator:
        if validator_id not in self._validators:
            raise KeyError(f"unknown validator: {validator_id}")
        return self._validators[validator_id]

    @classmethod
    def defaults(cls) -> "ValidatorRegistry":
        registry = cls()
        registry.register(JsonParseValidator())
        registry.register(JsonSchemaValidator())
        registry.register(RequiredFieldsValidator())
        registry.register(NoAdditionalPropertiesValidator())
        registry.register(UniqueIdsValidator())
        registry.register(ScopeEvidenceValidator())
        registry.register(ForbiddenTermsValidator())
        registry.register(EvidenceRequiredValidator())
        registry.register(NumericPreservationValidator())
        registry.register(ExplicitTestCountValidator())
        registry.register(TestRequirementCoverageValidator())
        registry.register(CrossFieldConsistencyValidator())
        return registry


def _validate_schema(value: Any, schema: Dict[str, Any], path: str = "") -> List[str]:
    errors: List[str] = []
    expected_type = schema.get("type")
    if expected_type == "object":
        if not isinstance(value, dict):
            return [f"{path or 'value'} must be object"]
        for field in schema.get("required", []):
            if field not in value:
                errors.append(f"{path + '.' if path else ''}{field} is required")
        if schema.get("additionalProperties") is False:
            allowed = set(schema.get("properties", {}).keys())
            for field in sorted(set(value.keys()) - allowed):
                errors.append(f"{path + '.' if path else ''}{field} is not allowed")
        for field, field_schema in schema.get("properties", {}).items():
            if field in value and isinstance(field_schema, dict):
                errors.extend(_validate_schema(value[field], field_schema, f"{path + '.' if path else ''}{field}"))
    elif expected_type == "array" and not isinstance(value, list):
        errors.append(f"{path or 'value'} must be array")
    elif expected_type == "string" and not isinstance(value, str):
        errors.append(f"{path or 'value'} must be string")
    elif expected_type == "integer" and not isinstance(value, int):
        errors.append(f"{path or 'value'} must be integer")
    elif expected_type == "boolean" and not isinstance(value, bool):
        errors.append(f"{path or 'value'} must be boolean")
    return errors


def _get_path(value: Any, path: str) -> Any:
    current = value
    for part in path.split("."):
        if not part:
            continue
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _flatten_text(value: Any, ignored_keys: Iterable[str] = ()) -> List[str]:
    ignored = set(ignored_keys)
    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, dict):
        texts: List[str] = []
        for key, nested in value.items():
            if str(key) in ignored:
                continue
            texts.extend(_flatten_text(nested, ignored_keys=ignored))
        return texts
    if isinstance(value, list):
        texts = []
        for item in value:
            texts.extend(_flatten_text(item, ignored_keys=ignored))
        return texts
    return [str(value)]


def _is_searchable_term(term: str) -> bool:
    normalized = term.strip()
    if len(normalized) < 3:
        return False
    return any(character.isalpha() for character in normalized)


def _dedupe_terms(terms: Iterable[str]) -> List[str]:
    seen = set()
    result = []
    for term in terms:
        normalized = " ".join(str(term).split())
        key = normalized.casefold()
        if not normalized or key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def _normalize_for_search(value: str) -> str:
    replacements = {
        "\u00e4": "ae",
        "\u00f6": "oe",
        "\u00fc": "ue",
        "\u00df": "ss",
    }
    normalized = value.casefold()
    for source, replacement in replacements.items():
        normalized = normalized.replace(source, replacement)
    return normalized


def _extract_numbers(text: str) -> List[str]:
    numbers = []
    for match in re.finditer(r"(?<![\w])\d+(?:[.,]\d+)?\s*(?:%|prozent|percent)?", text, flags=re.IGNORECASE):
        normalized = match.group(0).strip().casefold().replace(",", ".")
        normalized = re.sub(r"\s+", " ", normalized)
        if normalized.endswith("%"):
            normalized = normalized[:-1].strip() + " prozent"
        if normalized.endswith(" percent"):
            normalized = normalized[: -len(" percent")] + " prozent"
        numbers.append(normalized)
    return _dedupe_terms(numbers)


def _configured_required_terms(configuration: Dict[str, Any]) -> List[str]:
    return [str(term) for term in configuration.get("required_terms", []) if str(term).strip()]


def _terms_from_paths(payload: Dict[str, Any], paths: Any) -> List[str]:
    terms = []
    for path in _list_items(paths):
        terms.extend(_flatten_text(_get_path(payload, str(path))))
    return [term for term in terms if _is_searchable_term(term)]


def _evidence_terms(payload: Dict[str, Any], configuration: Dict[str, Any]) -> List[str]:
    configured = _configured_required_terms({"required_terms": configuration.get("evidence_terms", [])})
    paths = configuration.get(
        "evidence_paths",
        [
            "requirement_analysis.input_summary",
            "requirement_analysis.in_scope",
            "requirement_analysis.core_facts",
            "requirement_analysis.test_requirements",
            "requirement_analysis.quality_requirements",
        ],
    )
    return _dedupe_terms(configured + _terms_from_paths(payload, paths))


def _candidate_feature_terms(value: Any, configuration: Dict[str, Any]) -> List[str]:
    paths = configuration.get(
        "checked_paths",
        [
            "architecture_drivers",
            "context",
            "building_blocks",
            "runtime_scenarios",
            "architecture_decisions",
            "test_strategy",
            "test_requirements",
        ],
    )
    terms = []
    for path in _list_items(paths):
        terms.extend(_flatten_text(_get_path(value, str(path))))
    return [term for term in _dedupe_terms(terms) if _is_searchable_term(term)]


def _has_evidence(term: str, evidence_terms: List[str]) -> bool:
    normalized = _normalize_for_search(term)
    evidence_text = _normalize_for_search(" ".join(evidence_terms))
    if normalized in evidence_text:
        return True
    return any(_normalize_for_search(evidence) in normalized for evidence in evidence_terms if len(evidence) >= 4)


def _test_requirement_terms(test_requirements: Any) -> List[str]:
    terms = []
    for item in _list_items(test_requirements):
        if isinstance(item, dict):
            for key in ("type", "name", "coverage"):
                terms.extend(_flatten_text(item.get(key)))
            for text in _flatten_text(item.get("description")):
                terms.extend(_extract_numbers(text))
                terms.extend(_known_test_terms(text))
        else:
            terms.extend(_flatten_text(item))
    return [term for term in terms if _is_searchable_term(term) or _extract_numbers(term)]


def _coverage_terms(requirement_analysis: Dict[str, Any]) -> List[str]:
    terms = []
    for key in ("quality_goals", "quality_requirements", "acceptance_criteria", "core_facts"):
        for text in _flatten_text(requirement_analysis.get(key)):
            lowered = _normalize_for_search(text)
            if "coverage" in lowered or "testabdeckung" in lowered or "test" in lowered:
                terms.extend(_extract_numbers(text))
    return terms


def _list_items(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _known_test_terms(text: str) -> List[str]:
    normalized = _normalize_for_search(text)
    terms = []
    for term in ("unit", "medium", "integration", "coverage", "testabdeckung"):
        if term in normalized:
            terms.append(term)
    return terms


def _selected_terms(value: Any, rule: Dict[str, Any]) -> List[str]:
    field = rule.get("term_field")
    if isinstance(value, list) and field:
        terms = []
        for item in value:
            if isinstance(item, dict):
                terms.extend(_flatten_text(item.get(str(field))))
        return _dedupe_terms(terms)
    return _dedupe_terms(_flatten_text(value))
