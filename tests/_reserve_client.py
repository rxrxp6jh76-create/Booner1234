#!/usr/bin/env python3
import os
import sys
import asyncio

async def main():
    resource = sys.argv[1]
    owner = sys.argv[2]
    ttl = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    # Set SQLITE_DB_PATH must be inherited from parent env
    try:
        from backend.database_v2 import db_manager
        db = await db_manager.get_instance()
        success = await db.trades_db.reserve_resource('commodity', resource, owner, ttl_seconds=ttl)
        if success:
            print('OK')
            sys.exit(0)
        else:
            print('FAIL')
            sys.exit(2)
    except Exception as e:
        print('ERROR', str(e))
        sys.exit(3)

if __name__ == '__main__':
    asyncio.run(main())
