from linear_algebra.registry import catalog_registry
from linear_algebra.validation import validate_registry


def test_complete_registry_has_no_reference_or_capability_errors() -> None:
    errors = validate_registry(catalog_registry())
    assert errors == ()
