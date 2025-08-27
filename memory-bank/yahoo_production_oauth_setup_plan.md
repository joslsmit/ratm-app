# Yahoo OAuth Production Setup Plan

> **File Type**: IMPLEMENTATION PLAN  
> **Priority**: HIGH - Required for Yahoo features to work in production  
> **Created**: August 27, 2025  
> **Status**: Ready for implementation  

## Current Issue
Yahoo OAuth login fails in production with error: "Yahoo client ID or secret not configured on the server"

**Root Cause**: Two missing pieces for production Yahoo integration:
1. Environment variables not set in Render dashboard
2. Redirect URI hardcoded to localhost instead of production URL

## Required Yahoo OAuth Credentials
You need these from your Yahoo Developer Console (https://developer.yahoo.com/apps/):
- **YAHOO_CLIENT_ID**: Your app's client identifier  
- **YAHOO_CLIENT_SECRET**: Your app's client secret
- **FLASK_SECRET_KEY**: Secure random key for Flask sessions

## Implementation Plan

### Step 1: Set Environment Variables in Render (SECURE METHOD ✅)
**Location**: Render Dashboard > ratm-app service > Environment tab

**Add these environment variables**:
```
YAHOO_CLIENT_ID = [Your Yahoo app client ID from developer console]
YAHOO_CLIENT_SECRET = [Your Yahoo app client secret from developer console]  
FLASK_SECRET_KEY = [Generate with: python -c 'import secrets; print(secrets.token_hex(16))']
```

**Security Confirmation**: ✅ This is the recommended secure method
- Environment variables in Render are encrypted and not visible in code
- Only accessible to the running application, not in source control
- Standard practice for production deployments with sensitive credentials

### Step 2: Update Production Redirect URI in Code
**File**: `/backend/app.py`  
**Line**: ~2377 (search for YAHOO_REDIRECT_URI)

**Change from**:
```python
YAHOO_REDIRECT_URI = 'https://localhost:5000/api/yahoo/callback'
```

**Change to**:
```python
YAHOO_REDIRECT_URI = 'https://ratm-app.onrender.com/api/yahoo/callback'
```

### Step 3: Update Yahoo Developer Console
**Location**: Yahoo Developer Console > Your App Settings > Redirect URIs

**Add production callback URL**:
```
https://ratm-app.onrender.com/api/yahoo/callback
```

**Keep existing localhost URL** for local development:
```
https://localhost:5000/api/yahoo/callback
```

### Step 4: Deploy Changes
1. Commit redirect URI change to git
2. Push to main branch
3. Render automatically redeploys with new environment variables and code
4. Test Yahoo login at https://ratm-app.vercel.app

## Verification Steps
After implementation, verify:
1. ✅ Environment variables set in Render dashboard
2. ✅ Production redirect URI updated in code  
3. ✅ Yahoo app allows production callback URL
4. ✅ Render service redeployed successfully
5. ✅ Yahoo "Sign In" button works on production site
6. ✅ OAuth flow completes and returns to app successfully

## Expected Results
- Yahoo OAuth login functional in production
- All Yahoo-integrated features operational (roster analysis, waiver wire, market inefficiency)
- Users can authenticate with Yahoo and access personalized features

## Technical Notes
- **Memory Bank Reference**: techContext.md confirms "Environment Variables: Must be set manually in the Render dashboard"
- **Security Best Practice**: Never commit OAuth secrets to source control
- **Development vs Production**: Local development uses localhost redirect, production uses ratm-app.onrender.com
- **Auto-Deployment**: Changes to main branch automatically trigger Render redeployment

## Fallback Plan
If issues persist:
1. Check Render service logs for detailed error messages
2. Verify environment variables are correctly set (no typos)
3. Confirm Yahoo Developer Console redirect URI exactly matches code
4. Test OAuth flow step-by-step using browser developer tools

## Next Steps After Implementation
Once Yahoo OAuth is working:
- Monitor production usage and performance
- Consider adding error handling improvements
- Document any additional production-specific configurations needed