"""Standalone Pydantic & JSON demonstration script.

This file is a standalone learning example kept separate from the Sage application.
"""

import json
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ValidationError


# ==========================================
# 3. Pydantic BaseModel representing Incident
# ==========================================
class Incident(BaseModel):
    incident_id: str
    service: str
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]  # Strict allowed values
    timestamp: datetime                                    # Auto-parsed from ISO string
    error_count: int
    is_resolved: bool = False                              # Optional with default value


def main():
    print("=== STEP 1: Raw JSON String ===")
    json_string = """
    {
        "incident_id": "INC-1001",
        "service": "payment-service",
        "severity": "HIGH",
        "timestamp": "2026-09-02T08:30:00Z",
        "error_count": 15
    }
    """
    print(json_string.strip())

    print("\n=== STEP 2: Parse JSON to Python dict (json.loads) ===")
    parsed_dict = json.loads(json_string)
    print("Type:", type(parsed_dict))
    print("Value:", parsed_dict)

    print("\n=== STEP 4: Validate with Pydantic (model_validate) ===")
    incident = Incident.model_validate(parsed_dict)
    print("Type:", type(incident))
    print("Object:", incident)
    print("Accessing strongly-typed field -> incident.timestamp type:", type(incident.timestamp))
    print("Accessing default field -> incident.is_resolved:", incident.is_resolved)

    print("\n=== STEP 5: Serialize Back (model_dump & model_dump_json) ===")
    # 5a. Convert Pydantic object -> Python dict
    dict_output = incident.model_dump()
    print("Dict output (type:", type(dict_output), "):", dict_output)

    # 5b. Convert Pydantic object -> JSON string
    json_output = incident.model_dump_json(indent=2)
    print("\nJSON output (type:", type(json_output), "):\n" + json_output)

    print("\n" + "=" * 50)
    print("=== WHAT HAPPENS WHEN VALIDATION FAILS? ===")
    print("=" * 50)

    # Scenario A: Invalid Severity
    print("\n[Case A] Invalid severity ('SUPER_CRITICAL'):")
    invalid_severity_data = {
        "incident_id": "INC-1002",
        "service": "order-service",
        "severity": "SUPER_CRITICAL",  # <--- Not in Literal allowed set
        "timestamp": "2026-09-02T08:30:00Z",
        "error_count": 5,
    }
    try:
        Incident.model_validate(invalid_severity_data)
    except ValidationError as e:
        print("Caught ValidationError:")
        print(e)

    # Scenario B: Missing Required Field
    print("\n[Case B] Missing required field ('service' missing):")
    missing_field_data = {
        "incident_id": "INC-1003",
        # "service" is missing
        "severity": "LOW",
        "timestamp": "2026-09-02T08:30:00Z",
        "error_count": 1,
    }
    try:
        Incident.model_validate(missing_field_data)
    except ValidationError as e:
        print("Caught ValidationError:")
        print(e)


if __name__ == "__main__":
    main()
