#!/usr/bin/env python3
"""Live integration tests for Phase 7 tools (ACL, Quota, Password).

Run against a real Webmin server using the local webmin-servers.json config.
This script is NOT part of the automated test suite (no test_ prefix in pytest).

Usage:
    python tests/live_test_phase7.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import load_multi_server_config
from src.webmin_client import WebminClient
from src.tools import acl, quota


def print_result(label, result):
    """Pretty-print a ToolResult."""
    status = "OK" if result.success else "FAIL"
    print(f"\n{'='*60}")
    print(f"[{status}] {label}")
    print(f"{'='*60}")
    if result.success:
        print(json.dumps(result.data, indent=2, default=str))
    else:
        print(f"  Error: {result.error.code} - {result.error.message}")


async def test_acl_tools(client):
    """Test ACL (Webmin user management) tools."""
    print("\n" + "#"*60)
    print("# ACL MODULE TESTS (Read-only)")
    print("#"*60)

    # 1. List Webmin users
    result = await acl.list_webmin_users(client)
    print_result("list_webmin_users", result)

    # 2. Get details for first user found
    if result.success and result.data["users"]:
        first_user = result.data["users"][0]["name"]
        result2 = await acl.get_webmin_user(client, first_user)
        print_result(f"get_webmin_user('{first_user}')", result2)

    # 3. Get non-existent user
    result3 = await acl.get_webmin_user(client, "nonexistent_test_user_xyz")
    print_result("get_webmin_user('nonexistent_test_user_xyz')", result3)

    # 4. List Webmin modules
    result4 = await acl.list_webmin_modules(client)
    print_result("list_webmin_modules", result4)


async def test_quota_tools(client):
    """Test quota (disk quota management) tools."""
    print("\n" + "#"*60)
    print("# QUOTA MODULE TESTS (Read-only)")
    print("#"*60)

    # 1. List quota filesystems
    result = await quota.list_quota_filesystems(client)
    print_result("list_quota_filesystems", result)

    # 2. List user quotas on root filesystem
    result2 = await quota.list_user_quotas(client, "/")
    print_result("list_user_quotas('/')", result2)

    # 3. Get user quota for root on /
    result3 = await quota.get_user_quota(client, "root", "/")
    print_result("get_user_quota('root', '/')", result3)

    # 4. Get group quota for root on /
    result4 = await quota.get_group_quota(client, "root", "/")
    print_result("get_group_quota('root', '/')", result4)

    # 5. Set quota blocked in safe mode
    result5 = await quota.set_user_quota(
        client, username="root", filesystem="/",
        soft_block_limit=1000, hard_block_limit=2000,
        safe_mode=True,
    )
    print_result("set_user_quota (safe_mode=True, should be blocked)", result5)


async def test_acl_write_tools(client):
    """Test ACL write operations (create, modify, delete)."""
    print("\n" + "#"*60)
    print("# ACL MODULE TESTS (Write - safe_mode blocked)")
    print("#"*60)

    # 1. Create blocked in safe mode
    result = await acl.create_webmin_user(
        client, username="testuser_mcp", password="test123", safe_mode=True,
    )
    print_result("create_webmin_user (safe_mode=True, should be blocked)", result)

    # 2. Modify blocked in safe mode
    result2 = await acl.modify_webmin_user(
        client, username="admin", password="newpass", safe_mode=True,
    )
    print_result("modify_webmin_user (safe_mode=True, should be blocked)", result2)

    # 3. Delete blocked in safe mode
    result3 = await acl.delete_webmin_user(
        client, username="admin", safe_mode=True,
    )
    print_result("delete_webmin_user (safe_mode=True, should be blocked)", result3)


async def main():
    # Load config
    try:
        config = load_multi_server_config()
    except Exception as e:
        print(f"Failed to load config: {e}")
        print("Make sure webmin-servers.json exists.")
        sys.exit(1)

    alias, server = config.get_server()
    print(f"Connecting to: {alias} ({server.host}:{server.port})")
    print(f"Safe mode: {server.safe_mode}")

    wc = server.to_webmin_config()

    async with WebminClient(wc) as client:
        # Verify connection first
        try:
            version = await client.get_version()
            print(f"Connected! Webmin version: {version}")
        except Exception as e:
            print(f"Connection failed: {e}")
            sys.exit(1)

        # Run read-only tests
        await test_acl_tools(client)
        await test_quota_tools(client)

        # Run write tests (all should be blocked by safe_mode)
        await test_acl_write_tools(client)

    print("\n" + "="*60)
    print("Live tests complete!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
