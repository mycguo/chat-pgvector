# OAuth Redirect URI Configuration Guide

## Current Issue
Error: `redirect_uri_mismatch` - The redirect URI `https://job-search-assistant.streamlit.app/oauth2callback` is not registered in Google Cloud Console.

## Option 1: Register the Redirect URI in Google Cloud Console (Recommended)

This is the simplest solution if you want to keep using Streamlit's built-in OAuth.

### Steps:

1. **Go to Google Cloud Console**
   - Navigate to https://console.cloud.google.com/
   - Select your project (or create one if needed)

2. **Configure OAuth Consent Screen (Required First Step)**
   - Go to **APIs & Services** > **OAuth consent screen**
   - If not configured, select **External** (unless you have a Google Workspace)
   - Fill in required fields:
     - App name: Your app name
     - User support email: Your email
     - Developer contact information: Your email
   - Click **Save and Continue**
   - Skip scopes for now (click **Save and Continue**)
   - Skip test users (click **Save and Continue**)
   - Review and go back to dashboard

3. **Navigate to OAuth 2.0 Credentials**
   - Go to **APIs & Services** > **Credentials**
   - Look for existing OAuth 2.0 Client IDs

4. **Create or Edit OAuth 2.0 Client ID**
   
   **If you DON'T have an OAuth 2.0 Client ID:**
   - Click **+ CREATE CREDENTIALS** at the top
   - Select **OAuth client ID**
   - If prompted, select **Web application** as the application type
   - Give it a name (e.g., "Streamlit App")
   - **IMPORTANT**: Under **Authorized redirect URIs**, click **+ ADD URI**
   - Add exactly: `https://job-search-assistant.streamlit.app/oauth2callback`
   - Click **CREATE**
   - **Save the Client ID and Client Secret** - you'll need these for Streamlit Cloud

   **If you ALREADY have an OAuth 2.0 Client ID:**
   - Click on the OAuth 2.0 Client ID name to edit it
   - **Check the Application type** - it MUST be "Web application" (not "Desktop app" or "iOS/Android")
   - If it's NOT "Web application":
     - You need to create a NEW one (follow steps above)
     - Or change the type (if possible in your console)
   - Scroll down to find **Authorized redirect URIs** section
   - Click **+ ADD URI**
   - Add exactly: `https://job-search-assistant.streamlit.app/oauth2callback`
   - **Important**: The URI must match exactly (including `https://`, no trailing slash)

5. **Save Changes**
   - Click **SAVE** at the bottom (or **UPDATE** if creating new)

### Troubleshooting: Can't Find "Authorized redirect URIs"

**Problem**: The "Authorized redirect URIs" section doesn't appear.

**Solutions**:
1. **Check Application Type**: Make sure your OAuth client is type "Web application", not "Desktop app" or "Chrome app"
   - Desktop apps don't have redirect URIs
   - Only Web applications have this section

2. **Create a New Web Application Client**:
   - If your existing client is the wrong type, create a new one:
   - Go to **Credentials** > **+ CREATE CREDENTIALS** > **OAuth client ID**
   - Select **Web application** (this is crucial!)
   - The redirect URI section will appear automatically

3. **Check Your View**:
   - Make sure you're viewing the full edit page, not just the summary
   - Click on the client ID name (not just view it)
   - Scroll down - the section might be below the fold

4. **Verify OAuth Consent Screen**:
   - Make sure you've completed the OAuth consent screen setup first
   - Go to **APIs & Services** > **OAuth consent screen** and complete it

6. **Configure Streamlit Cloud**
   - In your Streamlit Cloud dashboard, go to your app settings
   - Add your OAuth credentials to the app's secrets:
     - `oauth_client_id`: Your Google OAuth Client ID
     - `oauth_client_secret`: Your Google OAuth Client Secret
     - `oauth_provider`: `google`

### For Local Development:

If you're testing locally, you'll also need to add:
- `http://localhost:8501/oauth2callback` (or your local port)

## Option 2: Change the Redirect URI (Custom OAuth Implementation)

If you want to use a different redirect URI, you'll need to implement custom OAuth instead of using `st.login()`. This requires:

1. **Modifying the authentication code** to use a custom OAuth flow
2. **Updating Google Cloud Console** with your new redirect URI
3. **Handling the OAuth callback manually**

### Implementation Steps:

1. Install required packages:
   ```bash
   pip install google-auth google-auth-oauthlib google-auth-httplib2
   ```

2. Create a custom OAuth handler (see example below)
3. Update `storage/auth_utils.py` to use the custom implementation
4. Register your new redirect URI in Google Cloud Console

### Example Custom OAuth Implementation:

```python
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
import streamlit as st
import os

# OAuth 2.0 configuration
CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
REDIRECT_URI = "https://your-custom-domain.com/oauth2callback"  # Your custom URI
SCOPES = ['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile']

def get_oauth_flow():
    """Create and return OAuth flow"""
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI]
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    return flow

def login_custom():
    """Custom login function"""
    flow = get_oauth_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    st.session_state['oauth_state'] = state
    st.markdown(f'[Click here to login]({authorization_url})')
```

## Recommendation

**Use Option 1** unless you have a specific reason to change the redirect URI. Streamlit Cloud's built-in OAuth is simpler and more secure.

## Additional Notes

- The redirect URI format for Streamlit Cloud is always: `https://<app-name>.streamlit.app/oauth2callback`
- For local development, use: `http://localhost:<port>/oauth2callback`
- Make sure your OAuth consent screen is configured in Google Cloud Console
- The redirect URI must be registered before it can be used

