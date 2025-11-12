# Data Encryption Setup Guide

This application supports transparent encryption of user data at rest. All JSON files and vector store metadata are automatically encrypted when a master key is configured.

## Quick Start

### 1. Install the cryptography library

```bash
pip install cryptography
```

### 2. Generate a master encryption key

```bash
python generate_encryption_key.py
```

This will output a key like:
```
ENCRYPTION_MASTER_KEY = "gAAAAABh..."
```

### 3. Configure the master key

**Option A: Streamlit Secrets** (Recommended for production)

Add to `.streamlit/secrets.toml`:
```toml
ENCRYPTION_MASTER_KEY = "your_generated_key_here"
```

**Option B: Environment Variable**

```bash
export ENCRYPTION_MASTER_KEY="your_generated_key_here"
```

### 4. Restart the application

Once the master key is configured, all new data will be automatically encrypted. Existing unencrypted data will continue to work (backward compatible).

## How It Works

- **User-specific keys**: Each user gets a unique encryption key derived from the master key + their user ID
- **Transparent encryption**: Data is automatically encrypted when written and decrypted when read
- **Backward compatible**: Existing unencrypted files continue to work
- **Secure**: Uses Fernet symmetric encryption (AES-128 in CBC mode with HMAC)

## What Gets Encrypted

- ✅ All JSON database files (`applications.json`, `resumes.json`, `questions.json`, etc.)
- ✅ Vector store metadata files (`metadata.json`)
- ❌ Vector embeddings (`vectors.pkl`) - These are binary and less sensitive
- ❌ Resume PDF files - Stored as-is (can be added later if needed)

## Security Notes

⚠️ **IMPORTANT:**
- Never commit the master key to git
- Store the master key securely (use secrets management)
- If you lose the master key, encrypted data cannot be recovered
- Each user's data is encrypted with a unique key derived from their user ID

## Disabling Encryption

To disable encryption, simply remove or don't set the `ENCRYPTION_MASTER_KEY`. The application will continue to work with unencrypted data.

## Migration

The system automatically handles migration:
- If encryption is enabled but files are unencrypted, they're read as plain JSON
- New writes will be encrypted
- Old encrypted files continue to work if the key is correct

