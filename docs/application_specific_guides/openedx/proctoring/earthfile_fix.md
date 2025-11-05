# Earthfile Configuration Fix for Proctoring Worker Bundles

**Date:** November 5, 2024  
**Issue:** Missing `workers.json` and `webpack-worker-stats.json` in compiled assets  
**Root Cause:** Django initialization step missing from build process

## Problem Summary

The MIT ODL Earthfile build process for Open edX is missing critical steps to generate proctoring JavaScript worker bundles. This results in:

1. ❌ `workers.json` never created
2. ❌ Webpack silently skips worker bundle builds
3. ❌ `webpack-worker-stats.json` not generated
4. ❌ Proctoring JavaScript functionality broken at runtime

## Current Build Flow (Broken)

```earthfile
build-static-assets-nonprod:
  FROM +fetch-translations
  ENV JS_ENV_EXTRA_CONFIG '{"PROCTORTRACK_CDN_URL": "...", "PROCTORTRACK_CONFIG_KEY": "..."}'
  
  # Install some editable packages
  RUN pip install ...
  
  ENV STATIC_ROOT_LMS=/openedx/staticfiles/
  ENV NODE_ENV=prod
  
  # Current broken sequence:
  RUN mkdir -p $STATIC_ROOT_LMS && npm run postinstall \
    && npm run compile-sass -- --theme-dir /openedx/themes/ --theme $DEPLOYMENT_NAME \
    && python manage.py lms collectstatic --noinput --settings=mitol.assets \
    && python manage.py cms collectstatic --noinput --settings=mitol.assets \
    && npm run webpack 2> /dev/null \  # ← FAILS HERE: workers.json doesn't exist!
    && python manage.py lms collectstatic --noinput --settings=mitol.assets \
    && python manage.py cms collectstatic --noinput --settings=mitol.assets
```

### Why It Fails

1. **Line 178:** `npm run webpack 2> /dev/null` runs webpack
2. Webpack tries to load `../workers.json` (from edx-platform directory)
3. File doesn't exist (Django never initialized to create it)
4. Webpack's try/catch silently returns empty config
5. No worker bundles are built
6. Errors suppressed by `2> /dev/null`

## Required Fixes

### Fix 1: Update Django Settings Files

**File:** `dockerfiles/openedx-edxapp/settings/lms/assets.not_py`

**Current content:**
```python
# -*- mode: python -*-
"""
Bare minimum settings for collecting production assets.
"""
from ..common import *
from openedx.core.lib.derived import derive_settings

ENABLE_COMPREHENSIVE_THEMING = True
COMPREHENSIVE_THEME_DIRS.append("/openedx/themes")

STATIC_ROOT_BASE = "/openedx/staticfiles"

SECRET_KEY = "secret"
XQUEUE_INTERFACE = {"django_auth": None, "url": None}
DATABASES = {"default": {}}

LMS_ROOT_URL = 'lms.example.com'

derive_settings(__name__)

LOCALE_PATHS.append("/openedx/locale/contrib/locale")
LOCALE_PATHS.append("/openedx/locale/user/locale")

PROCTORING_BACKENDS = {
    "DEFAULT": "proctortrack",
    "proctortrack": {
        "client_id": "",
        "client_secret": "",
        "base_url": "",
    },
}
```

**Add these lines after `STATIC_ROOT_BASE`:**
```python
STATIC_ROOT_BASE = "/openedx/staticfiles"

# Required for workers.json generation
NODE_MODULES_ROOT = "/openedx/edx-platform/node_modules"
ENV_ROOT = "/openedx"
```

**File:** `dockerfiles/openedx-edxapp/settings/cms/assets.not_py`

Apply the same changes to the CMS settings file.

### Fix 2: Update Earthfile Build Steps

**File:** `dockerfiles/openedx-edxapp/Earthfile`

**In both `build-static-assets-nonprod` and `build-static-assets-production` targets:**

**Replace lines 172-183 (approximately):**

```earthfile
# OLD (BROKEN):
RUN mkdir -p $STATIC_ROOT_LMS && npm run postinstall \
  && npm run compile-sass -- --theme-dir /openedx/themes/ --theme $DEPLOYMENT_NAME \
  && python manage.py lms collectstatic --noinput --settings=mitol.assets \
  && python manage.py cms collectstatic --noinput --settings=mitol.assets \
  && npm run webpack 2> /dev/null \
  && python manage.py lms collectstatic --noinput --settings=mitol.assets \
  && python manage.py cms collectstatic --noinput --settings=mitol.assets
```

**With:**

```earthfile
# NEW (FIXED):
RUN mkdir -p $STATIC_ROOT_LMS && npm run postinstall \
  && npm run compile-sass -- --theme-dir /openedx/themes/ --theme $DEPLOYMENT_NAME \
  && python manage.py lms collectstatic --noinput --settings=mitol.assets \
  && python manage.py cms collectstatic --noinput --settings=mitol.assets \
  && echo "=== Generating workers.json ===" \
  && python manage.py lms shell --settings=mitol.assets -c "print('Django apps initialized')" \
  && echo "=== Contents of workers.json ===" \
  && cat /openedx/workers.json \
  && echo "=== Running webpack ===" \
  && npm run webpack \
  && echo "=== Webpack complete ===" \
  && python manage.py lms collectstatic --noinput --settings=mitol.assets \
  && python manage.py cms collectstatic --noinput --settings=mitol.assets
```

### Key Changes Explained

1. **Added Django initialization:**
   ```bash
   python manage.py lms shell --settings=mitol.assets -c "print('Django apps initialized')"
   ```
   - This triggers Django app startup
   - `edx_proctoring` app's `ready()` method runs
   - `workers.json` gets generated

2. **Added verification step:**
   ```bash
   cat /openedx/workers.json
   ```
   - Shows workers.json contents in build logs
   - Helps verify correct generation
   - Easy to debug if file is empty or malformed

3. **Removed error suppression:**
   ```bash
   # Changed from:
   npm run webpack 2> /dev/null
   
   # To:
   npm run webpack
   ```
   - Shows actual webpack errors
   - Critical for debugging build issues
   - Prevents silent failures

4. **Added progress markers:**
   ```bash
   echo "=== Generating workers.json ==="
   echo "=== Running webpack ==="
   ```
   - Makes build logs easier to read
   - Helps identify which step failed

## Verification

### After Building

Check that these files exist in your built assets:

```bash
# Extract and check the tarball
tar -tzf staticfiles-nonprod.tar.gz | grep -E "(workers\.json|webpack-worker-stats\.json|edx-proctoring-proctortrack\.js)"

# Should show:
# openedx/workers.json
# openedx/staticfiles/webpack-worker-stats.json
# openedx/staticfiles/bundles/edx-proctoring-proctortrack.js
```

### Inspect workers.json

```bash
# During build, check the output:
=== Contents of workers.json ===
{
  "edx-proctoring-proctortrack": [
    "babel-polyfill",
    "/openedx/edx-platform/node_modules/edx-proctoring-proctortrack/edx_proctoring_proctortrack/static/proctortrack_custom.js"
  ]
}
```

### Check webpack-worker-stats.json

```bash
# After build:
cat /openedx/staticfiles/webpack-worker-stats.json

# Should show something like:
{
  "status": "done",
  "chunks": {
    "edx-proctoring-proctortrack": [
      {
        "name": "edx-proctoring-proctortrack.js",
        "path": "/openedx/staticfiles/bundles/edx-proctoring-proctortrack.js"
      }
    ]
  }
}
```

## Why JS_ENV_EXTRA_CONFIG Still Needed

Even with these fixes, you **cannot eliminate** `JS_ENV_EXTRA_CONFIG` because:

### Proctortrack's JavaScript Code

```javascript
// edx-proctoring-proctortrack/static/proctortrack_custom.js (lines 3-4)
const CDN_URL = process.env.JS_ENV_EXTRA_CONFIG.PROCTORTRACK_CDN_URL;
const KEY = process.env.JS_ENV_EXTRA_CONFIG.PROCTORTRACK_CONFIG_KEY;
```

### Webpack DefinePlugin

```javascript
// webpack.common.config.js
new webpack.DefinePlugin({
    'process.env.JS_ENV_EXTRA_CONFIG': 
        JSON.parse(process.env.JS_ENV_EXTRA_CONFIG)
})
```

**These values are replaced at compile time**, not runtime. The proctortrack code directly references environment variables that webpack must inject during the build.

### To Eliminate JS_ENV_EXTRA_CONFIG

You would need to:

1. Fork `edx-proctoring-proctortrack`
2. Modify the JavaScript to fetch config at runtime instead of compile time
3. Change from:
   ```javascript
   const CDN_URL = process.env.JS_ENV_EXTRA_CONFIG.PROCTORTRACK_CDN_URL;
   ```
   To:
   ```javascript
   const getConfig = () => {
       // Fetch from API or read from DOM at runtime
       return window.PROCTORTRACK_CONFIG || {};
   };
   ```
4. Maintain your fork indefinitely

**This is not recommended** - just accept that `JS_ENV_EXTRA_CONFIG` is required.

## Complete Fix Summary

### Files to Modify

1. ✅ `dockerfiles/openedx-edxapp/settings/lms/assets.not_py`
   - Add `NODE_MODULES_ROOT`
   - Add `ENV_ROOT`

2. ✅ `dockerfiles/openedx-edxapp/settings/cms/assets.not_py`
   - Add `NODE_MODULES_ROOT`
   - Add `ENV_ROOT`

3. ✅ `dockerfiles/openedx-edxapp/Earthfile`
   - Add Django initialization step before webpack
   - Remove error suppression from webpack
   - Add verification steps

### Settings Required

```python
# In both lms/assets.not_py and cms/assets.not_py:
NODE_MODULES_ROOT = "/openedx/edx-platform/node_modules"
ENV_ROOT = "/openedx"

# Already present (keep as-is):
PROCTORING_BACKENDS = {
    "DEFAULT": "proctortrack",
    "proctortrack": { ... }
}
```

### Environment Variables Required

```bash
# At webpack build time (already present in Earthfile):
export JS_ENV_EXTRA_CONFIG='{"PROCTORTRACK_CDN_URL":"...","PROCTORTRACK_CONFIG_KEY":"..."}'
```

## Testing the Fix

### Local Testing

```bash
# Build with the fixed Earthfile
earthly +build-static-assets-nonprod

# Check the output for:
# "=== Generating workers.json ==="
# "{...}" (the JSON content)
# "=== Running webpack ==="
# Should see webpack progress, not errors
```

### Verify Output

```bash
# Extract tarball
tar -xzf staticfiles-nonprod.tar.gz -C /tmp/test-static

# Check critical files exist
ls -la /tmp/test-static/openedx/workers.json
ls -la /tmp/test-static/openedx/staticfiles/webpack-worker-stats.json
ls -la /tmp/test-static/openedx/staticfiles/bundles/edx-proctoring-proctortrack.js

# All three should exist and be non-empty
```

## Historical Context

These settings have been **required since December 2018** (6+ years):

- **December 14, 2018:** `make_worker_config()` function added
- **December 17, 2018:** `NODE_MODULES_ROOT` requirement added  
- **October 23, 2019:** `ENV_ROOT` explicitly used for output path

The MIT ODL custom `assets.not_py` settings files didn't inherit from standard `lms/envs/common.py`, so they never got these settings. The build appeared to work because webpack's try/catch silently caught the error.

## See Also

- [Proctoring JS Architecture](./proctoring_js_architecture.md)
- [workers.json Generation Requirements](./workers_json_requirements.md)
- [Proctortrack Specific Issues](./proctortrack_build_issues.md)
