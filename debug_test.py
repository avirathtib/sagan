import asyncio
import asyncpg
import os
from dotenv import load_dotenv
load_dotenv()

async def debug_rds_connection():
    host = os.getenv("PG_HOST")
    port = int(os.getenv("PG_PORT", 5432))
    database = os.getenv("PG_DB")
    user = os.getenv("PG_RO_USER")
    password = os.getenv("PG_RO_PW")
    
    print(f"Testing RDS connection:")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Database: {database}")  
    print(f"User: {user}")
    print(f"Password: {'*' * len(password) if password else 'NOT SET'}")
    
    # Test different SSL modes
    ssl_modes = ["require", "prefer", "disable"]
    
    for ssl_mode in ssl_modes:
        print(f"\n--- Testing with SSL mode: {ssl_mode} ---")
        try:
            conn = await asyncpg.connect(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password,
                ssl=ssl_mode,
                command_timeout=30
            )
            
            # Test a simple query
            result = await conn.fetchval("SELECT 1")
            print(f"✓ SUCCESS with SSL={ssl_mode}")
            print(f"Test query result: {result}")
            
            await conn.close()
            break
            
        except asyncpg.InvalidAuthorizationSpecificationError as e:
            print(f"✗ Authentication failed: {e}")
            break  # No point trying other SSL modes
            
        except asyncpg.InvalidCatalogNameError as e:
            print(f"✗ Database '{database}' not found: {e}")
            break  # No point trying other SSL modes
            
        except Exception as e:
            print(f"✗ Failed with SSL={ssl_mode}: {e}")
            print(f"Error type: {type(e).__name__}")
            continue

# Run the test
asyncio.run(debug_rds_connection())