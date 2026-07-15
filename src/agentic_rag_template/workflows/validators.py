"""Reusable validators for workflow outputs."""

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol


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

