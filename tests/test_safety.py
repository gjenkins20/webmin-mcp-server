"""Tests for the safety framework."""

import pytest

from src.safety import (
    BLOCKED_SERVICES,
    RESTART_ONLY_SERVICES,
    SafetyCheckResult,
    SafetyTier,
    check_safety,
    check_service_operation,
    get_operation_tier,
    safety_check_or_fail,
)


class TestSafetyTier:
    """Tests for SafetyTier enum."""

    def test_tier_values(self) -> None:
        """Test that all tiers have correct values."""
        assert SafetyTier.READ == "read"
        assert SafetyTier.SAFE == "safe"
        assert SafetyTier.MODERATE == "moderate"
        assert SafetyTier.DANGEROUS == "dangerous"


class TestGetOperationTier:
    """Tests for get_operation_tier function."""

    def test_read_operations(self) -> None:
        """Test that read operations have READ tier."""
        assert get_operation_tier("status") == SafetyTier.READ
        assert get_operation_tier("list") == SafetyTier.READ

    def test_safe_operations(self) -> None:
        """Test that safe operations have SAFE tier."""
        assert get_operation_tier("enable") == SafetyTier.SAFE

    def test_moderate_operations(self) -> None:
        """Test that moderate operations have MODERATE tier."""
        assert get_operation_tier("start") == SafetyTier.MODERATE
        assert get_operation_tier("stop") == SafetyTier.MODERATE
        assert get_operation_tier("restart") == SafetyTier.MODERATE
        assert get_operation_tier("disable") == SafetyTier.MODERATE

    def test_dangerous_operations(self) -> None:
        """Test that dangerous operations have DANGEROUS tier."""
        assert get_operation_tier("delete") == SafetyTier.DANGEROUS
        assert get_operation_tier("remove") == SafetyTier.DANGEROUS

    def test_unknown_operation_defaults_to_moderate(self) -> None:
        """Test that unknown operations default to MODERATE."""
        assert get_operation_tier("unknown") == SafetyTier.MODERATE


class TestBlockedServices:
    """Tests for blocked services list."""

    def test_ssh_services_blocked(self) -> None:
        """Test that SSH services are in blocked list."""
        assert "ssh" in BLOCKED_SERVICES
        assert "sshd" in BLOCKED_SERVICES

    def test_webmin_blocked(self) -> None:
        """Test that webmin is in blocked list."""
        assert "webmin" in BLOCKED_SERVICES

    def test_systemd_services_blocked(self) -> None:
        """Test that critical systemd services are blocked."""
        assert "systemd-journald" in BLOCKED_SERVICES
        assert "systemd-networkd" in BLOCKED_SERVICES
        assert "dbus" in BLOCKED_SERVICES


class TestRestartOnlyServices:
    """Tests for restart-only services list."""

    def test_cron_in_restart_only(self) -> None:
        """Test that cron is in restart-only list."""
        assert "cron" in RESTART_ONLY_SERVICES


class TestCheckServiceOperation:
    """Tests for check_service_operation function."""

    def test_stop_blocked_service_not_allowed(self) -> None:
        """Test that stopping a blocked service is not allowed."""
        result = check_service_operation("sshd", "stop", safe_mode=True)
        assert not result.allowed
        assert "critical service" in result.reason.lower()

    def test_disable_blocked_service_not_allowed(self) -> None:
        """Test that disabling a blocked service is not allowed."""
        result = check_service_operation("webmin", "disable", safe_mode=True)
        assert not result.allowed
        assert "critical service" in result.reason.lower()

    def test_restart_blocked_service_in_safe_mode_not_allowed(self) -> None:
        """Test that restarting a blocked service in safe mode is not allowed."""
        result = check_service_operation("sshd", "restart", safe_mode=True)
        assert not result.allowed
        assert "safe mode" in result.reason.lower()

    def test_restart_blocked_service_without_safe_mode_allowed(self) -> None:
        """Test that restarting a blocked service without safe mode is allowed."""
        result = check_service_operation("sshd", "restart", safe_mode=False)
        assert result.allowed

    def test_stop_restart_only_service_in_safe_mode_not_allowed(self) -> None:
        """Test that stopping a restart-only service in safe mode is not allowed."""
        result = check_service_operation("cron", "stop", safe_mode=True)
        assert not result.allowed
        assert "safe mode" in result.reason.lower()

    def test_stop_restart_only_service_without_safe_mode_allowed(self) -> None:
        """Test that stopping a restart-only service without safe mode is allowed."""
        result = check_service_operation("cron", "stop", safe_mode=False)
        assert result.allowed

    def test_restart_restart_only_service_allowed(self) -> None:
        """Test that restarting a restart-only service is allowed."""
        result = check_service_operation("cron", "restart", safe_mode=True)
        assert result.allowed

    def test_regular_service_operations_allowed(self) -> None:
        """Test that operations on regular services are allowed."""
        result = check_service_operation("nginx", "stop", safe_mode=True)
        assert result.allowed

        result = check_service_operation("nginx", "restart", safe_mode=True)
        assert result.allowed

    def test_case_insensitive_service_names(self) -> None:
        """Test that service name matching is case-insensitive."""
        result = check_service_operation("SSHD", "stop", safe_mode=True)
        assert not result.allowed

        result = check_service_operation("SSH", "disable", safe_mode=True)
        assert not result.allowed


class TestCheckSafety:
    """Tests for check_safety function."""

    def test_dangerous_operation_blocked_in_safe_mode(self) -> None:
        """Test that dangerous operations are blocked in safe mode."""
        result = check_safety("delete", target="some_user", safe_mode=True)
        assert not result.allowed
        assert "dangerous" in result.reason.lower()

    def test_dangerous_operation_allowed_without_safe_mode(self) -> None:
        """Test that dangerous operations are allowed without safe mode."""
        result = check_safety("delete", target="some_user", safe_mode=False)
        assert result.allowed

    def test_read_operation_always_allowed(self) -> None:
        """Test that read operations are always allowed."""
        result = check_safety("status", target="sshd", safe_mode=True)
        assert result.allowed

    def test_service_operation_delegates_to_service_check(self) -> None:
        """Test that service operations use service-specific checks."""
        result = check_safety("stop", target="sshd", safe_mode=True)
        assert not result.allowed
        assert "critical service" in result.reason.lower()


class TestSafetyCheckOrFail:
    """Tests for safety_check_or_fail convenience function."""

    def test_returns_none_when_allowed(self) -> None:
        """Test that None is returned when operation is allowed."""
        result = safety_check_or_fail("restart", target="nginx", safe_mode=True)
        assert result is None

    def test_returns_tool_result_when_blocked(self) -> None:
        """Test that ToolResult is returned when operation is blocked."""
        result = safety_check_or_fail("stop", target="sshd", safe_mode=True)
        assert result is not None
        assert not result.success
        assert result.error.code == "SAFETY_BLOCKED"
