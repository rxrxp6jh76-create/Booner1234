import os
import subprocess
import tempfile
import time

import pytest

@pytest.mark.skipif(False, reason="Multiprocess DB tests")
def test_db_reservations_multiprocess():
    # Use a temporary DB file for this test
    with tempfile.TemporaryDirectory() as tmp:
        db_file = os.path.join(tmp, 'trades_multi.db')
        os.environ['SQLITE_DB_PATH'] = db_file

        resource = 'MT5_LIBERTEX_DEMO:GOLD'
        owner1 = 'proc1'
        owner2 = 'proc2'

        # Start two processes almost simultaneously
        p1 = subprocess.Popen(['python3', 'tests/_reserve_client.py', resource, owner1, '20'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(0.1)
        p2 = subprocess.Popen(['python3', 'tests/_reserve_client.py', resource, owner2, '20'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        out1, err1 = p1.communicate(timeout=10)
        out2, err2 = p2.communicate(timeout=10)

        s1 = out1.decode().strip()
        s2 = out2.decode().strip()

        # Exactly one should be OK
        oks = [s for s in (s1, s2) if s == 'OK']
        fails = [s for s in (s1, s2) if s == 'FAIL']

        assert len(oks) == 1, f"Expected exactly one OK, got: {s1!r}, {s2!r}" 
        assert len(fails) == 1, f"Expected one FAIL, got: {s1!r}, {s2!r}"