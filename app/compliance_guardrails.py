"""
Compliance Guardrails System: Implements before/after callback validation for Infrastructure Genie.
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import asyncio
from datetime import datetime


class GuardrailSeverity(Enum):
    """Severity levels for guardrail violations."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class GuardrailAction(Enum):
    """Actions to take on guardrail violations."""
    ALLOW = "allow"           # Allow with warning
    SANITIZE = "sanitize"     # Clean and allow
    BLOCK = "block"           # Block the request/response
    AUDIT = "audit"           # Log for review


@dataclass
class GuardrailViolation:
    """Represents a guardrail violation."""
    rule_name: str
    severity: GuardrailSeverity
    action: GuardrailAction
    message: str
    details: Dict[str, Any]
    timestamp: datetime


class ComplianceGuardrails:
    """Main guardrails system with before/after callbacks."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.violations: List[GuardrailViolation] = []

        # Compliance patterns to detect and block
        self.security_patterns = {
            'api_keys': r'(?i)(api[_-]?key|apikey|access[_-]?token|secret[_-]?key|private[_-]?key)["\']?\s*[:=]\s*["\']?[a-zA-Z0-9_\-]{20,}',
            'passwords': r'(?i)(password|passwd|pwd)["\']?\s*[:=]\s*["\']?[^\s"\']{8,}',
            'aws_access_keys': r'AKIA[0-9A-Z]{16}',
            'gcp_service_keys': r'"type":\s*"service_account"',
            'ssh_private_keys': r'-----BEGIN.*PRIVATE KEY-----',
            'database_urls': r'(?i)(mysql|postgres|mongodb|redis)://[^\s]+',
            'credit_cards': r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
            'social_security': r'\b\d{3}-\d{2}-\d{4}\b'
        }

        # Content compliance patterns
        self.content_patterns = {
            'malicious_commands': r'(?i)(rm\s+-rf|format\s+c:|del\s+/s|sudo\s+rm|chmod\s+777)',
            'sensitive_paths': r'(?i)(/etc/passwd|/etc/shadow|C:\\Windows\\System32)',
            'injection_attempts': r'(?i)(union\s+select|drop\s+table|exec\s*\(|eval\s*\(|script\s*>)',
            'inappropriate_content': r'(?i)(hack|exploit|vulnerability|penetration\s+test)',
        }

        # Infrastructure compliance rules
        self.infrastructure_patterns = {
            'hardcoded_ips': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
            'insecure_protocols': r'(?i)(http://|ftp://|telnet://)',
            'weak_encryption': r'(?i)(md5|sha1|des|rc4)',
            'default_credentials': r'(?i)(admin:admin|root:root|user:password)',
        }

    async def validate_input(self, query: str, context: Dict[str, Any] = None) -> tuple[bool, List[GuardrailViolation]]:
        """Before callback: Validate input before processing."""
        violations = []

        # Security validation
        violations.extend(await self._check_security_patterns(query, "input"))

        # Content validation
        violations.extend(await self._check_content_patterns(query, "input"))

        # Infrastructure validation
        violations.extend(await self._check_infrastructure_patterns(query, "input"))

        # Context validation
        if context:
            violations.extend(await self._validate_context(context))

        # Business logic validation
        violations.extend(await self._validate_business_rules(query, context))

        # Determine if request should be blocked
        should_block = any(v.action == GuardrailAction.BLOCK for v in violations)

        # Log violations
        for violation in violations:
            self._log_violation(violation)
            self.violations.append(violation)

        return not should_block, violations

    async def validate_output(self, output: str, specialist_name: str, context: Dict[str, Any] = None) -> tuple[str, List[GuardrailViolation]]:
        """After callback: Validate and sanitize output before returning."""
        violations = []
        sanitized_output = output

        # Security validation on output
        violations.extend(await self._check_security_patterns(output, "output"))

        # Content validation on output
        violations.extend(await self._check_content_patterns(output, "output"))

        # Infrastructure validation on output
        violations.extend(await self._check_infrastructure_patterns(output, "output"))

        # Specialist-specific validation
        violations.extend(await self._validate_specialist_output(output, specialist_name))

        # Sanitize output based on violations
        for violation in violations:
            if violation.action == GuardrailAction.SANITIZE:
                sanitized_output = await self._sanitize_content(sanitized_output, violation)
            elif violation.action == GuardrailAction.BLOCK:
                sanitized_output = f"[BLOCKED: Output violated compliance policy - {violation.rule_name}]"
                break

        # Apply additional sanitization for infrastructure patterns
        for violation in violations:
            if "hardcoded_ips" in violation.rule_name:
                sanitized_output = await self._sanitize_content(sanitized_output, violation)

        # Log violations
        for violation in violations:
            self._log_violation(violation)
            self.violations.append(violation)

        return sanitized_output, violations

    async def _check_security_patterns(self, text: str, context_type: str) -> List[GuardrailViolation]:
        """Check for security-related patterns."""
        violations = []

        for pattern_name, pattern in self.security_patterns.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                violations.append(GuardrailViolation(
                    rule_name=f"security_{pattern_name}",
                    severity=GuardrailSeverity.CRITICAL,
                    action=GuardrailAction.BLOCK if context_type == "output" else GuardrailAction.SANITIZE,
                    message=f"Detected {pattern_name} in {context_type}",
                    details={
                        "pattern": pattern_name,
                        "match": match.group()[:50] + "..." if len(match.group()) > 50 else match.group(),
                        "position": match.span(),
                        "context": context_type
                    },
                    timestamp=datetime.now()
                ))

        return violations

    async def _check_content_patterns(self, text: str, context_type: str) -> List[GuardrailViolation]:
        """Check for inappropriate content patterns."""
        violations = []

        for pattern_name, pattern in self.content_patterns.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                severity = GuardrailSeverity.CRITICAL if pattern_name == "malicious_commands" else GuardrailSeverity.WARNING
                action = GuardrailAction.BLOCK if severity == GuardrailSeverity.CRITICAL else GuardrailAction.AUDIT

                violations.append(GuardrailViolation(
                    rule_name=f"content_{pattern_name}",
                    severity=severity,
                    action=action,
                    message=f"Detected {pattern_name} in {context_type}",
                    details={
                        "pattern": pattern_name,
                        "match": match.group(),
                        "context": context_type
                    },
                    timestamp=datetime.now()
                ))

        return violations

    async def _check_infrastructure_patterns(self, text: str, context_type: str) -> List[GuardrailViolation]:
        """Check for infrastructure compliance patterns."""
        violations = []

        for pattern_name, pattern in self.infrastructure_patterns.items():
            matches = re.finditer(pattern, text)
            for match in matches:
                violations.append(GuardrailViolation(
                    rule_name=f"infrastructure_{pattern_name}",
                    severity=GuardrailSeverity.WARNING,
                    action=GuardrailAction.AUDIT,
                    message=f"Detected {pattern_name} in {context_type}",
                    details={
                        "pattern": pattern_name,
                        "match": match.group(),
                        "context": context_type,
                        "recommendation": self._get_security_recommendation(pattern_name)
                    },
                    timestamp=datetime.now()
                ))

        return violations

    async def _validate_context(self, context: Dict[str, Any]) -> List[GuardrailViolation]:
        """Validate context parameters."""
        violations = []

        # Check for sensitive data in context
        context_str = json.dumps(context, default=str)
        violations.extend(await self._check_security_patterns(context_str, "context"))

        return violations

    async def _validate_business_rules(self, query: str, context: Dict[str, Any] = None) -> List[GuardrailViolation]:
        """Validate business-specific rules."""
        violations = []

        # Example: Restrict certain types of requests during business hours
        current_hour = datetime.now().hour
        if 9 <= current_hour <= 17:  # Business hours
            if re.search(r'(?i)(delete|destroy|terminate|remove)', query):
                violations.append(GuardrailViolation(
                    rule_name="business_hours_restriction",
                    severity=GuardrailSeverity.WARNING,
                    action=GuardrailAction.AUDIT,
                    message="Destructive operations flagged during business hours",
                    details={
                        "query": query[:100],
                        "time": datetime.now().isoformat(),
                        "recommendation": "Consider scheduling for off-hours"
                    },
                    timestamp=datetime.now()
                ))

        # Example: Require approval for production deployments
        if re.search(r'(?i)(production|prod|live)', query):
            violations.append(GuardrailViolation(
                rule_name="production_deployment",
                severity=GuardrailSeverity.INFO,
                action=GuardrailAction.AUDIT,
                message="Production deployment detected",
                details={
                    "query": query[:100],
                    "recommendation": "Ensure proper approval process"
                },
                timestamp=datetime.now()
            ))

        return violations

    async def _validate_specialist_output(self, output: str, specialist_name: str) -> List[GuardrailViolation]:
        """Validate specialist-specific output."""
        violations = []

        if specialist_name == "terraform_specialist":
            # Validate Terraform code doesn't have dangerous configurations
            if re.search(r'(?i)(allow_all|0\.0\.0\.0/0|public_access.*true)', output):
                violations.append(GuardrailViolation(
                    rule_name="terraform_security",
                    severity=GuardrailSeverity.WARNING,
                    action=GuardrailAction.AUDIT,
                    message="Terraform configuration may have security issues",
                    details={
                        "specialist": specialist_name,
                        "issue": "Overly permissive access detected"
                    },
                    timestamp=datetime.now()
                ))

        elif specialist_name == "microsoft_specialist":
            # Validate Azure recommendations don't include deprecated services
            deprecated_services = ['Classic VM', 'Cloud Services (classic)', 'Service Fabric Mesh']
            for service in deprecated_services:
                if service.lower() in output.lower():
                    violations.append(GuardrailViolation(
                        rule_name="azure_deprecated_service",
                        severity=GuardrailSeverity.WARNING,
                        action=GuardrailAction.AUDIT,
                        message=f"Deprecated Azure service mentioned: {service}",
                        details={
                            "specialist": specialist_name,
                            "service": service
                        },
                        timestamp=datetime.now()
                    ))

        return violations

    async def _sanitize_content(self, content: str, violation: GuardrailViolation) -> str:
        """Sanitize content based on violation type."""
        if "api_keys" in violation.rule_name or "passwords" in violation.rule_name:
            # Replace sensitive data with placeholders
            pattern = violation.details.get("match", "")
            content = content.replace(pattern, "[REDACTED_CREDENTIAL]")

        elif "hardcoded_ips" in violation.rule_name:
            # Replace IP addresses with placeholders
            content = re.sub(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', '[IP_ADDRESS]', content)

        return content

    def _get_security_recommendation(self, pattern_name: str) -> str:
        """Get security recommendations for patterns."""
        recommendations = {
            'hardcoded_ips': 'Use environment variables or configuration files for IP addresses',
            'insecure_protocols': 'Use HTTPS, SFTP, or SSH instead of insecure protocols',
            'weak_encryption': 'Use strong encryption algorithms like AES-256, SHA-256, or newer',
            'default_credentials': 'Always change default credentials and use strong passwords'
        }
        return recommendations.get(pattern_name, 'Review security best practices')

    def _log_violation(self, violation: GuardrailViolation):
        """Log violation based on severity."""
        log_message = f"Guardrail {violation.rule_name}: {violation.message}"

        if violation.severity == GuardrailSeverity.CRITICAL:
            self.logger.critical(log_message, extra={"violation": violation.details})
        elif violation.severity == GuardrailSeverity.ERROR:
            self.logger.error(log_message, extra={"violation": violation.details})
        elif violation.severity == GuardrailSeverity.WARNING:
            self.logger.warning(log_message, extra={"violation": violation.details})
        else:
            self.logger.info(log_message, extra={"violation": violation.details})

    async def get_compliance_report(self) -> Dict[str, Any]:
        """Generate compliance report."""
        total_violations = len(self.violations)

        severity_counts = {}
        for severity in GuardrailSeverity:
            severity_counts[severity.value] = sum(1 for v in self.violations if v.severity == severity)

        rule_counts = {}
        for violation in self.violations:
            rule_counts[violation.rule_name] = rule_counts.get(violation.rule_name, 0) + 1

        return {
            "total_violations": total_violations,
            "severity_breakdown": severity_counts,
            "rule_breakdown": rule_counts,
            "recent_violations": [
                {
                    "rule": v.rule_name,
                    "severity": v.severity.value,
                    "action": v.action.value,
                    "message": v.message,
                    "timestamp": v.timestamp.isoformat()
                }
                for v in self.violations[-10:]  # Last 10 violations
            ]
        }

    def clear_violations(self):
        """Clear violation history."""
        self.violations.clear()


# Global instance
guardrails = ComplianceGuardrails()