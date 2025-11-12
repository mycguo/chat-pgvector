#!/usr/bin/env python3
"""
Generate a master encryption key for data encryption.

This script generates a secure master key that can be used to encrypt
user data. Store this key securely in your Streamlit secrets or environment variables.

Usage:
    python generate_encryption_key.py

Then add to your .streamlit/secrets.toml:
    ENCRYPTION_MASTER_KEY = "generated_key_here"

Or set as environment variable:
    export ENCRYPTION_MASTER_KEY="generated_key_here"
"""

from storage.encryption import generate_master_key

if __name__ == "__main__":
    print("=" * 60)
    print("Generating Master Encryption Key")
    print("=" * 60)
    print()
    
    try:
        key = generate_master_key()
        print("✅ Master key generated successfully!")
        print()
        print("Add this to your Streamlit secrets (.streamlit/secrets.toml):")
        print()
        print(f'ENCRYPTION_MASTER_KEY = "{key}"')
        print()
        print("Or set as environment variable:")
        print()
        print(f'export ENCRYPTION_MASTER_KEY="{key}"')
        print()
        print("⚠️  IMPORTANT: Keep this key secure and never commit it to git!")
        print("=" * 60)
    except ImportError:
        print("❌ Error: cryptography library is not installed.")
        print("   Install it with: pip install cryptography")
    except Exception as e:
        print(f"❌ Error generating key: {e}")

