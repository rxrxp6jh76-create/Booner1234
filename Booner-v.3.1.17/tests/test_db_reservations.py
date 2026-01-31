#!/usr/bin/env python3
"""
Simple tests for DB-backed reservations (multi-process simulation).

- Test 1: Two separate DB clients attempt to reserve the same resource concurrently - only one should succeed.
- Test 2: Reservation expires -> a second client can acquire it after TTL.
- Test 3: Owner-specific release allows takeover.

This file follows the project's standalone asyncio test style (not pytest).
"""

import asyncio
import os
import sys
from pathlib import Path
import logging
import shutil

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='[%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Add backend to path
backend_path = str(Path(__file__).parent.parent / "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from database_v2 import TradesDatabase, get_db_directory


async def setup_db_instance(temp_db_dir: Path):
    # Point env to a specific file path so both instances use the same file
    db_file = str(temp_db_dir / "trades_res_test.db")
    os.environ['SQLITE_DB_PATH'] = db_file

    db1 = TradesDatabase()
    await db1.connect()
    await db1.initialize_schema()
    return db1


async def test_reservation_competition():
    print("\n" + "=" * 70)
    print("TEST 1: Concurrent reservation competition (one should win)")
    print("=" * 70)

    tmp_dir = Path("/tmp/test_db_reservations")
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    db_a = await setup_db_instance(tmp_dir)
    db_b = TradesDatabase()
    await db_b.connect()

    # Ensure schema present for both
    await db_b.initialize_schema()

    # Run two concurrent reservation attempts
    r1 = db_a.reserve_resource('commodity', 'GOLD', owner='proc_a', ttl_seconds=5)
    r2 = db_b.reserve_resource('commodity', 'GOLD', owner='proc_b', ttl_seconds=5)

    res = await asyncio.gather(r1, r2)
    logger.info(f"Reservation results: {res}")

    if (res.count(True) == 1 and res.count(False) == 1):
        print("✅ TEST 1 PASSED: Exactly one reservation succeeded")
        return True
    else:
        print("❌ TEST 1 FAILED: Reservation competition did not behave as expected")
        return False


async def test_reservation_expiry_and_release():
    print("\n" + "=" * 70)
    print("TEST 2: Reservation expiry and owner release")
    print("=" * 70)

    tmp_dir = Path("/tmp/test_db_reservations")
    tmp_dir.mkdir(parents=True, exist_ok=True)

    db1 = await setup_db_instance(tmp_dir)
    db2 = TradesDatabase()
    await db2.connect()

    # Reserve with short TTL
    ok1 = await db1.reserve_resource('commodity', 'SILVER', owner='owner1', ttl_seconds=1)
    logger.info(f"owner1 reserved: {ok1}")

    # Immediately second should fail
    ok2 = await db2.reserve_resource('commodity', 'SILVER', owner='owner2', ttl_seconds=1)
    logger.info(f"owner2 reserved immediately: {ok2}")

    # Wait for expiry
    await asyncio.sleep(1.2)

    # Now owner2 should succeed
    ok3 = await db2.reserve_resource('commodity', 'SILVER', owner='owner2', ttl_seconds=1)
    logger.info(f"owner2 reserved after expiry: {ok3}")

    # Test release by owner3 scenario
    ok4 = await db1.reserve_resource('commodity', 'COPPER', owner='ownerX', ttl_seconds=60)
    logger.info(f"ownerX reserved COPPER: {ok4}")
    # release by specific owner
    released = await db1.release_resource('commodity', 'COPPER', owner='ownerX')
    logger.info(f"ownerX released COPPER: {released}")
    ok5 = await db2.reserve_resource('commodity', 'COPPER', owner='ownerY', ttl_seconds=60)
    logger.info(f"ownerY reserved COPPER after release: {ok5}")

    if ok1 and not ok2 and ok3 and ok4 and released and ok5:
        print("✅ TEST 2 PASSED: Expiry and owner-specific release behaved correctly")
        return True
    else:
        print("❌ TEST 2 FAILED: Unexpected behavior in expiry/release")
        return False


async def main():
    results = []
    try:
        results.append(("Reservation competition", await test_reservation_competition()))
    except Exception as e:
        logger.exception(f"Test 1 crashed: {e}")
        results.append(("Reservation competition", False))

    try:
        results.append(("Expiry and release", await test_reservation_expiry_and_release()))
    except Exception as e:
        logger.exception(f"Test 2 crashed: {e}")
        results.append(("Expiry and release", False))

    print("\n" + "#" * 70)
    print("# TEST SUMMARY")
    print("#" * 70)
    for name, passed in results:
        print(("✅ PASS" if passed else "❌ FAIL") + f": {name}")

    if all(p for _, p in results):
        print("\n🎉 ALL DB RESERVATION TESTS PASSED")
        return 0
    else:
        print("\n❌ SOME DB RESERVATION TESTS FAILED")
        return 1


if __name__ == '__main__':
    rc = asyncio.run(main())
    sys.exit(rc)
