# Open edX Proctoring Build Issues - Investigation Summary

**Investigation Date:** November 5, 2024  
**Context:** MIT Open Learning (MIT ODL) Open edX Deployment  
**Issue:** Missing proctoring JavaScript worker bundles in compiled static assets

## Problem Statement

The MIT ODL Earthfile-based Docker build for Open edX was not generating the required JavaScript worker bundles for proctoring functionality, specifically for the Proctortrack proctoring provider.

**Missing files:**
- `workers.json` - Configuration file consumed by webpack
- `webpack-worker-stats.json` - Build manifest for worker bundles
- `edx-proctoring-proctortrack.js` - The actual worker bundle

## Root Cause

The build process had three missing components:

1. **Missing Django settings** (`NODE_MODULES_ROOT` and `ENV_ROOT`) in custom `assets.not_py` files
2. **No Django initialization step** before webpack runs in the Earthfile
3. **Silent error suppression** (`2> /dev/null`) hiding webpack failures

These caused `workers.json` to never be generated, resulting in webpack silently skipping the worker bundle builds.

## Key Findings

### JS 1.0 vs JS 2.0 Are NOT Different Versions

The terms "JS 1.0" and "JS 2.0" caused confusion. They do **NOT** refer to:
- Different versions of proctoring JavaScript
- Different build processes
- Different webpack configurations

They **ONLY** refer to how the JavaScript worker URL is delivered to the frontend:
- **JS 1.0:** Embedded in Django template context variables (legacy LMS)
- **JS 2.0:** Returned via REST API responses (modern MFE)

**Both require the exact same build process** - the only difference is the delivery mechanism at runtime.

### Build-Time Requirements Cannot Be Eliminated

The `JS_ENV_EXTRA_CONFIG` environment variable **cannot be eliminated** because:

1. Proctortrack's JavaScript code directly references it at lines 3-4:
   ```javascript
   const CDN_URL = process.env.JS_ENV_EXTRA_CONFIG.PROCTORTRACK_CDN_URL;
   const KEY = process.env.JS_ENV_EXTRA_CONFIG.PROCTORTRACK_CONFIG_KEY;
   ```

2. Webpack's `DefinePlugin` replaces these at **compile time** (not runtime):
   ```javascript
   new webpack.DefinePlugin({
       'process.env.JS_ENV_EXTRA_CONFIG': JSON.parse(process.env.JS_ENV_EXTRA_CONFIG)
   })
   ```

The MFE approach (JS 2.0) does NOT eliminate this requirement - it only changes how the worker bundle URL is delivered to the frontend.

### Settings Have Been Required Since 2018

The `NODE_MODULES_ROOT` and `ENV_ROOT` settings are **not new**:

- **December 14, 2018:** `make_worker_config()` function added (commit c160a7a9)
- **December 17, 2018:** `NODE_MODULES_ROOT` check added (commit dd1f37a7)
- **October 23, 2019:** `ENV_ROOT` explicitly used (commit a7cd6847)

These settings have been in standard `lms/envs/common.py` for **6+ years**. The MIT ODL custom settings files didn't inherit them because they import from `openedx.core.lib.derived.common` instead of `lms.envs.common`.

## Solution

### Required Changes

1. **Update `settings/lms/assets.not_py` and `settings/cms/assets.not_py`:**
   ```python
   # Add after STATIC_ROOT_BASE:
   NODE_MODULES_ROOT = "/openedx/edx-platform/node_modules"
   ENV_ROOT = "/openedx"
   ```

2. **Update Earthfile build targets** (both nonprod and production):
   ```earthfile
   # Add before npm run webpack:
   && echo "=== Generating workers.json ===" \
   && python manage.py lms shell --settings=mitol.assets -c "print('Django initialized')" \
   && echo "=== Contents of workers.json ===" \
   && cat /openedx/workers.json \
   && echo "=== Running webpack ===" \
   && npm run webpack \  # Remove 2> /dev/null
   ```

3. **Keep `JS_ENV_EXTRA_CONFIG`** - it's required by proctortrack's implementation

## Documentation Index

This investigation produced four detailed documents:

1. **[proctoring_js_architecture.md](./proctoring_js_architecture.md)**
   - Explains JS 1.0 vs JS 2.0 in detail
   - Documents both approaches with code examples
   - Clarifies build-time vs runtime configuration
   - **Read this first** to understand the architecture

2. **[workers_json_requirements.md](./workers_json_requirements.md)**
   - Complete documentation of `workers.json` generation
   - Required Django settings explained
   - Verification steps and troubleshooting
   - Historical timeline of the feature

3. **[earthfile_fix.md](./earthfile_fix.md)**
   - Step-by-step fix for MIT ODL Earthfile
   - Before/after code comparisons
   - Verification procedures
   - Testing instructions
   - **Use this for implementation**

## Quick Reference

### Build Process Flow

```
1. Django app initialization (manage.py shell)
   └─> edx_proctoring.apps.ready()
       └─> make_worker_config()
           └─> Generates workers.json

2. Webpack reads workers.json
   └─> Builds worker bundles
       └─> Generates webpack-worker-stats.json

3. Django-webpack-loader reads webpack-worker-stats.json
   └─> Returns bundle URLs at runtime
       └─> JS 1.0: Template context
       └─> JS 2.0: API response
```

### Required Files Check

```bash
# After successful build, these must exist:
/openedx/workers.json
/openedx/staticfiles/webpack-worker-stats.json
/openedx/staticfiles/bundles/edx-proctoring-proctortrack.js
```

### Required Settings

```python
# In both lms/assets.not_py and cms/assets.not_py:
NODE_MODULES_ROOT = "/openedx/edx-platform/node_modules"
ENV_ROOT = "/openedx"

PROCTORING_BACKENDS = {
    "DEFAULT": "proctortrack",
    "proctortrack": {
        "client_id": "",
        "client_secret": "",
        "base_url": "",
    },
}
```

### Required Environment Variables

```bash
# At webpack build time:
export JS_ENV_EXTRA_CONFIG='{"PROCTORTRACK_CDN_URL":"https://...","PROCTORTRACK_CONFIG_KEY":"..."}'
```

## Testing

### Verify Fix Worked

```bash
# 1. Build with changes
earthly +build-static-assets-nonprod

# 2. Check build logs for:
#    "=== Generating workers.json ==="
#    "{...}" (JSON content)
#    "=== Running webpack ==="
#    Webpack progress output (no errors)

# 3. Extract and verify files
tar -xzf staticfiles-nonprod.tar.gz -C /tmp/test
ls -la /tmp/test/openedx/workers.json
ls -la /tmp/test/openedx/staticfiles/webpack-worker-stats.json  
ls -la /tmp/test/openedx/staticfiles/bundles/edx-proctoring-proctortrack.js
```

## Common Misconceptions Clarified

| ❌ Misconception | ✅ Reality |
|-----------------|-----------|
| "JS 2.0 eliminates build-time config" | Both JS 1.0 and 2.0 need identical build process |
| "MFE approach doesn't need workers.json" | MFE still needs worker bundles built by webpack |
| "JS_ENV_EXTRA_CONFIG is only for build time" | It's needed because proctortrack code references it |
| "These are new requirements" | Settings required since December 2018 (6+ years) |
| "JS 2.0 is a new proctoring system" | It's just a different URL delivery method |

## Timeline

### December 2018
- Worker bundle system introduced
- `NODE_MODULES_ROOT` required from day 1
- Used to support proctoring providers with JavaScript components

### October 2019
- `ENV_ROOT` explicitly required for output path
- Part of Python 3 compatibility updates

### May 2021
- MFE support added (JS 2.0)
- API endpoints return `desktop_application_js_url`
- Build requirements unchanged

### November 2024
- MIT ODL discovers missing worker bundles
- Investigation reveals missing Django settings
- Documentation created to prevent future confusion

## Contributing

If you encounter similar issues:

1. Check Django settings include `NODE_MODULES_ROOT` and `ENV_ROOT`
2. Verify Django initialization happens before webpack
3. Don't suppress webpack errors during debugging
4. Check `workers.json` exists and has correct content
5. Verify webpack-worker-stats.json is generated

## Repository Links

- edx-proctoring: https://github.com/openedx/edx-proctoring
- edx-proctoring-proctortrack: https://github.com/verificient/edx-proctoring-proctortrack
- frontend-lib-special-exams: https://github.com/openedx/frontend-lib-special-exams
- edx-platform: https://github.com/openedx/edx-platform
- MIT ODL infrastructure: https://github.com/mitodl/ol-infrastructure

## License

This documentation is provided as-is for educational and operational purposes.

---

**Questions or issues?** Reference the detailed documentation files linked above.
