import pytest
import json

def test_initial_state(direct_deploy):
    # Deploy contract and check initial count is 0
    contract = direct_deploy("contracts/pedagogical_age_oracle.py", sdk_version="v0.2.16")
    assert contract.get_total_evaluations() == 0

def test_input_validation(direct_deploy, direct_vm):
    contract = direct_deploy("contracts/pedagogical_age_oracle.py", sdk_version="v0.2.16")
    
    # Test empty material_snippet
    with pytest.raises(Exception) as excinfo:
        contract.evaluate_material("", "Grade 4, 9-10 years old")
    assert "material_snippet must not be empty" in str(excinfo.value)
    
    # Test empty target_age_group
    with pytest.raises(Exception) as excinfo:
        contract.evaluate_material("Some lesson text", "")
    assert "target_age_group must not be empty" in str(excinfo.value)

def test_evaluate_material_happy_path(direct_deploy, direct_vm):
    contract = direct_deploy("contracts/pedagogical_age_oracle.py", sdk_version="v0.2.16")
    
    # Mock LLM verdict
    direct_vm.mock_llm(
        r".*",
        '{"suitability": "APPROPRIATE", "confidence": 95, "feedback": "Vocabulary and tone are perfect for Grade 4."}'
    )
    
    # Execute evaluation
    contract.evaluate_material(
        material_snippet="In this lesson, we will learn how to add fractions with common denominators by drawing pie charts.",
        target_age_group="Grade 4, 9-10 years old"
    )
    
    assert contract.get_total_evaluations() == 1
    
    # Retrieve and parse record
    record_json = contract.get_evaluation("0")
    record = json.loads(record_json)
    
    assert record["id"] == "0"
    assert record["material_snippet"] == "In this lesson, we will learn how to add fractions with common denominators by drawing pie charts."
    assert record["target_age_group"] == "Grade 4, 9-10 years old"
    assert record["suitability"] == "APPROPRIATE"
    assert record["confidence"] == 95
    assert record["feedback"] == "Vocabulary and tone are perfect for Grade 4."
