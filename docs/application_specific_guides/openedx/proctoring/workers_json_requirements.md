# workers.json Generation Requirements

**Date:** November 5, 2024  
**Related to:** Open edX Proctoring JavaScript Build Process

## Overview

The `workers.json` file is a critical configuration file that enables webpack to build proctoring provider JavaScript bundles. This document explains what it is, why it's needed, and how to ensure it gets generated correctly.

## What is workers.json?

`workers.json` is a JSON configuration file that maps proctoring backend NPM package names to their JavaScript entry points. It's consumed by webpack to build Web Worker bundles for proctoring providers.

### Example Content

```json
{
  "edx-proctoring-proctortrack": [
    "babel-polyfill",
    "/openedx/edx-platform/node_modules/edx-proctoring-proctortrack/edx_proctoring_proctortrack/static/proctortrack_custom.js"
  ]
}
```

### Purpose

Webpack's `webpack.common.config.js` uses this file to determine:
1. Which proctoring providers need worker bundles
2. Where to find their JavaScript source code
3. What dependencies (like babel-polyfill) to include

## Generation Process

### When It's Created

The file is generated during **Django application initialization** when the `edx_proctoring` app's `ready()` method is called.

```python
# edx_proctoring/apps.py
class EdxProctoringConfig(AppConfig):
    def ready(self):
        # Load all proctoring backends
        self.backends = {}
        for extension in ExtensionManager(namespace='openedx.proctoring'):
            name = extension.name
            try:
                options = {
                    key: val for (key, val) in config[name].items()
                    if key in BACKEND_CONFIGURATION_ALLOW_LIST
                }
                self.backends[name] = extension.plugin(**options)
            except KeyError:
                pass
        
        # Generate workers.json
        make_worker_config(
            list(self.backends.values()), 
            out=os.path.join(settings.ENV_ROOT, 'workers.json')
        )
```

### Generation Logic

```python
def make_worker_config(backends, out='/tmp/workers.json'):
    """
    Generates a config json file used for edx-platform's webpack.common.config.js
    """
    # CRITICAL: Returns False if NODE_MODULES_ROOT not set
    if not getattr(settings, 'NODE_MODULES_ROOT', None):
        return False
    
    config = {}
    for backend in backends:
        try:
            # Get the npm_module attribute from backend
            package = backend.npm_module
            
            # Read package.json from node_modules
            package_file = os.path.join(
                settings.NODE_MODULES_ROOT, 
                package, 
                'package.json'
            )
            with open(package_file, 'r', encoding='utf-8') as package_fp:
                package_json = json.load(package_fp)
            
            # Get the main entry point
            main_file = package_json['main']
            
            # Add to config
            config[package] = [
                'babel-polyfill',
                os.path.join(settings.NODE_MODULES_ROOT, package, main_file)
            ]
        except AttributeError:
            # Backend doesn't have npm_module attribute
            continue
        except IOError:
            warnings.warn(
                f'Proctoring backend {backend.__class__} defined an npm module, '
                f'but it is not installed at {package_file!r}'
            )
        except KeyError:
            warnings.warn(f'{package_file!r} does not contain a `main` entry')
    
    if config:
        try:
            with open(out, 'wb+') as outfp:
                outfp.write(json.dumps(config).encode('utf-8'))
        except IOError:
            warnings.warn(f"Could not write worker config to {out}")
        else:
            os.chmod(out, 0o664)  # Make group writable
            return True
    return False
```

## Required Django Settings

### 1. NODE_MODULES_ROOT

**Required:** Yes  
**Purpose:** Points to the directory containing installed NPM packages  
**Typical Value:** `/openedx/edx-platform/node_modules`

```python
NODE_MODULES_ROOT = "/openedx/edx-platform/node_modules"
```

**Why it's needed:**
- Django needs to find the proctoring provider's NPM package
- Must read `package.json` to get the `main` entry point
- Must construct full path to the JavaScript file

### 2. ENV_ROOT

**Required:** Yes  
**Purpose:** Parent directory where `workers.json` will be written  
**Typical Value:** `/openedx`

```python
ENV_ROOT = "/openedx"
```

**Why it's needed:**
- Determines where `workers.json` is created
- Usually the parent of the edx-platform directory
- Webpack expects to find it at `../workers.json` relative to webpack.common.config.js

### 3. PROCTORING_BACKENDS

**Required:** Yes  
**Purpose:** Configuration for proctoring backends  

```python
PROCTORING_BACKENDS = {
    "DEFAULT": "proctortrack",
    "proctortrack": {
        "client_id": "your-client-id",
        "client_secret": "your-client-secret",
        "base_url": "https://testing.verificient.com",
    },
}
```

**Why it's needed:**
- Tells edx_proctoring which backends to load
- Without this, no backends are instantiated
- No backends = empty `workers.json` = no worker bundles built

## Standard edx-platform Settings

In a standard Open edX installation, these settings are defined in `lms/envs/common.py`:

```python
# From edx-platform/lms/envs/common.py (circa line 1117)
ENV_ROOT = REPO_ROOT.dirname()  # /edx-platform is in this dir
COURSES_ROOT = ENV_ROOT / "data"
NODE_MODULES_ROOT = REPO_ROOT / "node_modules"
```

These have been present since **December 2018** when the workers.json feature was first added.

## Required NPM Package

The proctoring backend's NPM package must be installed in `node_modules`.

### For Proctortrack:

```bash
npm install edx-proctoring-proctortrack
```

Or in `package.json`:

```json
{
  "dependencies": {
    "edx-proctoring-proctortrack": "^1.1.1"
  }
}
```

### Package Requirements:

The NPM package must have:

1. **package.json with main entry:**
   ```json
   {
     "name": "edx-proctoring-proctortrack",
     "main": "edx_proctoring_proctortrack/static/proctortrack_custom.js"
   }
   ```

2. **The npm_module attribute on the backend class:**
   ```python
   class ProctortrackBackendProvider(BaseRestProctoringProvider):
       npm_module = 'edx-proctoring-proctortrack'
   ```

## Verification Steps

### 1. Check if workers.json exists

```bash
ls -l /openedx/workers.json
cat /openedx/workers.json
```

### 2. Verify Django settings

```bash
python manage.py lms shell --settings=your.settings
>>> from django.conf import settings
>>> print(settings.NODE_MODULES_ROOT)
>>> print(settings.ENV_ROOT)
>>> print(settings.PROCTORING_BACKENDS)
```

### 3. Test workers.json generation

```bash
# This will initialize Django apps including edx_proctoring
python manage.py lms shell --settings=your.settings -c "print('Django initialized')"

# Check if workers.json was created
cat /openedx/workers.json
```

### 4. Verify NPM package

```bash
ls -l $NODE_MODULES_ROOT/edx-proctoring-proctortrack/
cat $NODE_MODULES_ROOT/edx-proctoring-proctortrack/package.json
```

## Common Issues

### Issue 1: workers.json not created

**Symptom:** File doesn't exist after Django initialization

**Causes:**
- `NODE_MODULES_ROOT` not set in Django settings
- `PROCTORING_BACKENDS` not configured
- NPM package not installed
- Backend doesn't have `npm_module` attribute

**Solution:**
```python
# Add to your settings file:
NODE_MODULES_ROOT = "/openedx/edx-platform/node_modules"
ENV_ROOT = "/openedx"
PROCTORING_BACKENDS = {
    "DEFAULT": "proctortrack",
    "proctortrack": { ... }
}
```

### Issue 2: Empty workers.json

**Symptom:** File exists but is `{}` or `null`

**Causes:**
- No backends configured
- Backend NPM packages not found
- Backend's `package.json` missing or invalid

**Solution:**
- Verify NPM packages are installed
- Check Django logs for warnings about missing packages
- Ensure backends are properly configured

### Issue 3: Webpack can't find workers.json

**Symptom:** Webpack build succeeds but no worker bundles

**Causes:**
- `workers.json` in wrong location
- Webpack looking in wrong place
- Try/catch in webpack config hiding the error

**Solution:**
```javascript
// In webpack.common.config.js
var workerConfig = function() {
    try {
        const config = require('../workers.json');
        console.log('Loaded workers.json:', config);
        return { webworker: { entry: config, ... } };
    } catch (err) {
        console.error('Failed to load workers.json:', err);
        return {};
    }
};
```

## Timeline

### December 14, 2018
- **Commit:** c160a7a9
- **Author:** Dave St.Germain
- **Change:** Initial implementation of `make_worker_config()`
- **Settings required:** `NODE_MODULES_ROOT` (from day 1)

### October 23, 2019
- **Commit:** a7cd6847
- **Author:** Ayub Khan
- **Change:** Explicitly use `settings.ENV_ROOT` for output path
- **Context:** Python 3 compatibility updates

### Present Day
- Both settings have been required for **6+ years**
- Part of standard edx-platform configuration
- Required for any proctoring backend with JavaScript workers

## Best Practices

1. **Always set both required settings** in any custom settings file:
   ```python
   NODE_MODULES_ROOT = "/path/to/node_modules"
   ENV_ROOT = "/path/to/project"
   ```

2. **Initialize Django before webpack** in build processes:
   ```bash
   python manage.py lms shell -c "print('workers.json generated')"
   npm run webpack
   ```

3. **Don't suppress webpack errors** during development:
   ```bash
   # Use this instead of npm run webpack 2>/dev/null
   npm run webpack
   ```

4. **Verify workers.json contents** after generation:
   ```bash
   test -f /openedx/workers.json && cat /openedx/workers.json || echo "ERROR: workers.json not found"
   ```

5. **Check file permissions** if writing fails:
   ```bash
   ls -la /openedx/workers.json
   # Should be writable by the user running Django
   ```

## See Also

- [Proctoring JS Architecture](./proctoring_js_architecture.md)
- [Earthfile Configuration Issues](./earthfile_analysis.md)
- [Proctortrack Build Issues](./proctortrack_build_issues.md)
