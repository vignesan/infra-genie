"""
Compliance API: Endpoints for monitoring and managing guardrails.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from app.compliance_guardrails import guardrails, GuardrailSeverity, GuardrailAction

router = APIRouter()


@router.get("/compliance/report")
async def get_compliance_report() -> Dict[str, Any]:
    """Get comprehensive compliance report."""
    try:
        report = await guardrails.get_compliance_report()
        return {
            "status": "success",
            "data": report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating compliance report: {str(e)}")


@router.get("/compliance/violations")
async def get_recent_violations(limit: int = 50) -> Dict[str, Any]:
    """Get recent guardrail violations."""
    try:
        recent_violations = [
            {
                "rule_name": v.rule_name,
                "severity": v.severity.value,
                "action": v.action.value,
                "message": v.message,
                "details": v.details,
                "timestamp": v.timestamp.isoformat()
            }
            for v in guardrails.violations[-limit:]
        ]

        return {
            "status": "success",
            "data": {
                "violations": recent_violations,
                "total_count": len(guardrails.violations)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching violations: {str(e)}")


@router.post("/compliance/test-input")
async def test_input_validation(query: str) -> Dict[str, Any]:
    """Test input validation against guardrails."""
    try:
        is_valid, violations = await guardrails.validate_input(query)

        violation_details = [
            {
                "rule_name": v.rule_name,
                "severity": v.severity.value,
                "action": v.action.value,
                "message": v.message,
                "details": v.details
            }
            for v in violations
        ]

        return {
            "status": "success",
            "data": {
                "is_valid": is_valid,
                "violations": violation_details,
                "blocked": any(v.action == GuardrailAction.BLOCK for v in violations)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing input: {str(e)}")


@router.post("/compliance/test-output")
async def test_output_validation(output: str, specialist_name: str = "test_specialist") -> Dict[str, Any]:
    """Test output validation and sanitization."""
    try:
        sanitized_output, violations = await guardrails.validate_output(output, specialist_name)

        violation_details = [
            {
                "rule_name": v.rule_name,
                "severity": v.severity.value,
                "action": v.action.value,
                "message": v.message,
                "details": v.details
            }
            for v in violations
        ]

        return {
            "status": "success",
            "data": {
                "original_output": output,
                "sanitized_output": sanitized_output,
                "was_sanitized": sanitized_output != output,
                "violations": violation_details
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing output: {str(e)}")


@router.delete("/compliance/violations")
async def clear_violations() -> Dict[str, Any]:
    """Clear violation history."""
    try:
        violations_count = len(guardrails.violations)
        guardrails.clear_violations()

        return {
            "status": "success",
            "message": f"Cleared {violations_count} violations from history"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing violations: {str(e)}")


@router.get("/compliance/health")
async def compliance_health_check() -> Dict[str, Any]:
    """Health check for compliance system."""
    try:
        report = await guardrails.get_compliance_report()

        # Determine health status
        critical_violations = report["severity_breakdown"].get("critical", 0)
        error_violations = report["severity_breakdown"].get("error", 0)

        if critical_violations > 0:
            health_status = "critical"
            health_message = f"{critical_violations} critical violations detected"
        elif error_violations > 10:
            health_status = "warning"
            health_message = f"{error_violations} error violations detected"
        else:
            health_status = "healthy"
            health_message = "Compliance system operating normally"

        return {
            "status": "success",
            "data": {
                "health_status": health_status,
                "message": health_message,
                "total_violations": report["total_violations"],
                "severity_breakdown": report["severity_breakdown"]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking compliance health: {str(e)}")