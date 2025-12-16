#!/usr/bin/env python3
"""
Diagnose Neon PostgreSQL connection issues.
"""
import os
import socket
import time

def check_dns_resolution(hostname):
    """Check if DNS resolves the hostname."""
    print(f"\n1. DNS Resolution Test for {hostname}")
    try:
        ip_address = socket.gethostbyname(hostname)
        print(f"   ✓ DNS resolves to: {ip_address}")
        return ip_address
    except socket.gaierror as e:
        print(f"   ✗ DNS resolution failed: {e}")
        return None

def check_port_connectivity(hostname, port, timeout=5):
    """Check if we can connect to the port."""
    print(f"\n2. Port Connectivity Test ({hostname}:{port})")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        start = time.time()
        result = sock.connect_ex((hostname, port))
        duration = time.time() - start
        sock.close()

        if result == 0:
            print(f"   ✓ Port {port} is reachable ({duration:.2f}s)")
            return True
        else:
            print(f"   ✗ Port {port} is not reachable (error code: {result})")
            return False
    except socket.timeout:
        print(f"   ✗ Connection timed out after {timeout}s")
        return False
    except Exception as e:
        print(f"   ✗ Connection failed: {e}")
        return False

def parse_neon_url(url):
    """Parse Neon database URL."""
    # Format: postgresql://user:password@host:port/database?sslmode=require
    if not url:
        return None

    try:
        # Remove protocol
        url = url.replace('postgresql://', '').replace('postgres://', '')

        # Split credentials from host
        if '@' in url:
            creds, rest = url.split('@', 1)
            # Split host from database
            if '/' in rest:
                host_port, db_params = rest.split('/', 1)
            else:
                host_port = rest
                db_params = ''

            # Extract host and port
            if ':' in host_port:
                host, port = host_port.rsplit(':', 1)
                # Remove port number suffix if it exists
                port = port.split('?')[0]
            else:
                host = host_port
                port = '5432'

            return {
                'host': host,
                'port': int(port),
                'credentials': creds.split(':')[0] if ':' in creds else creds
            }
    except Exception as e:
        print(f"Error parsing URL: {e}")

    return None

def main():
    print("=" * 70)
    print("Neon PostgreSQL Connection Diagnostics")
    print("=" * 70)

    # Get Neon URL from environment
    neon_url = os.getenv('NEON_DATABASE_URL')

    if not neon_url:
        print("\n✗ NEON_DATABASE_URL environment variable not set")
        print("\nTo set it, run:")
        print('export NEON_DATABASE_URL="postgresql://user:password@host/database"')
        return 1

    print(f"\n✓ NEON_DATABASE_URL is set")

    # Parse URL
    parsed = parse_neon_url(neon_url)

    if not parsed:
        print("\n✗ Could not parse Neon URL")
        return 1

    print(f"\nConnection details:")
    print(f"  Host: {parsed['host']}")
    print(f"  Port: {parsed['port']}")
    print(f"  User: {parsed['credentials']}")

    # Test DNS
    ip = check_dns_resolution(parsed['host'])

    if not ip:
        print("\n✗ DNS resolution failed - check your internet connection")
        return 1

    # Test port connectivity
    print("\nTesting connectivity with different timeouts...")

    # Try with increasing timeouts
    for timeout in [5, 10, 15]:
        print(f"\n  Attempt with {timeout}s timeout...")
        if check_port_connectivity(parsed['host'], parsed['port'], timeout):
            print(f"\n✓ Successfully connected with {timeout}s timeout")
            break
    else:
        print("\n✗ All connection attempts failed")
        print("\nPossible issues:")
        print("  1. Database is sleeping (Neon pauses databases after inactivity)")
        print("     → Try accessing your Neon dashboard to wake it up")
        print("  2. Firewall blocking outbound connections on port 5432")
        print("  3. IP allowlist restrictions on Neon")
        print("     → Check Neon dashboard → Settings → IP Allow")
        print("  4. Using connection pooler endpoint instead of direct endpoint")
        print("     → In Neon dashboard, try copying the 'Direct connection' string")

        print("\nRecommended actions:")
        print("  1. Visit https://console.neon.tech/")
        print("  2. Select your project")
        print("  3. Go to Dashboard to wake the database")
        print("  4. Check Connection Details for the correct endpoint")
        print("  5. Try the 'Direct connection' string instead of pooler")

        return 1

    print("\n" + "=" * 70)
    print("Network connectivity looks good!")
    print("=" * 70)

    print("\nIf you're still seeing timeout errors in the app:")
    print("  • The database might have gone to sleep again")
    print("  • Try increasing connection timeout in pg_connection.py")
    print("  • Consider using Neon's direct endpoint instead of pooler")

    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
