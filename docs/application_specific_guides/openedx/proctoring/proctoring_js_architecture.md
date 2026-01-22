# Open edX Proctoring JavaScript Architecture: JS 1.0 vs JS 2.0

**Date:** November 5, 2024  
**Author:** Investigation of edx-proctoring and edx-platform integration  
**Version:** 1.0

## Executive Summary

Open edX supports two different approaches for loading proctoring provider JavaScript code, commonly referred to as "JS 1.0" and "JS 2.0". Understanding the difference is critical for proper deployment configuration, especially when using containerized builds.

## Table of Contents

1. [Overview](#overview)
2. [JS 1.0: Legacy LMS Template Approach](#js-10-legacy-lms-template-approach)
3. [JS 2.0: Modern MFE API Approach](#js-20-modern-mfe-api-approach)
4. [Build-Time vs Runtime Configuration](#build-time-vs-runtime-configuration)
5. [Key Differences Summary](#key-differences-summary)

---

## Overview

The Open edX platform needs to load proctoring provider-specific JavaScript to communicate with desktop proctoring applications. There are two approaches:

- **JS 1.0**: JavaScript bundles embedded in Django templates (legacy approach)
- **JS 2.0**: JavaScript bundle URLs returned via REST API (modern MFE approach)

Both approaches can coexist in the same deployment and serve different frontend applications.

---

## JS 1.0: Legacy LMS Template Approach

### Architecture

In the traditional LMS courseware interface, proctoring JavaScript is loaded directly into Django-rendered HTML templates.

### How It Works

1. **Backend generates JavaScript bundle URL:**
   ```python
   # edx_proctoring/backends/rest.py
   def get_javascript(self):
       package = getattr(self, 'npm_module', self.__class__.__module__.split('.', maxsplit=1)[0])
       bundle_chunks = get_files(package, config="WORKERS")
       js_url = bundle_chunks[0]["url"]
       
       if not urlparse(js_url).scheme:
           if hasattr(settings, 'LMS_ROOT_URL'):
               js_url = settings.LMS_ROOT_URL + js_url
       
       return js_url
   ```

2. **Template context includes bundle URL:**
   ```python
   # edx_proctoring/api.py
   context = {
       'backend_js_bundle': provider.get_javascript(),
       ...
   }
   ```

3. **Template embeds the URL:**
   ```html
   <!-- edx_proctoring/templates/proctored_exam/ready_to_start.html -->
   <script type="text/javascript">
     var edx = edx || {};
     edx.courseware = edx.courseware || {};
     edx.courseware.proctored_exam = edx.courseware.proctored_exam || {};
     edx.courseware.proctored_exam.configuredWorkerURL = "{{ backend_js_bundle }}";
   </script>
   ```

4. **JavaScript creates Web Worker:**
   ```javascript
   // edx_proctoring/static/proctoring/js/exam_action_handler.js
   function createWorker(url) {
       var blob = new Blob(["importScripts('" + url + "');"], {type: 'application/javascript'});
       var blobUrl = window.URL.createObjectURL(blob);
       return new Worker(blobUrl);
   }
   
   var proctoringBackendWorker = createWorker(
       edx.courseware.proctored_exam.configuredWorkerURL
   );
   ```

### Configuration Requirements

**Build-Time:**
- Webpack must build proctoring worker bundles
- `webpack-worker-stats.json` must exist for django-webpack-loader
- `workers.json` must be generated before webpack runs

**Runtime:**
- Django settings must include proctoring backend configuration
- Templates must have access to `backend_js_bundle` variable

### Used By

- Traditional LMS courseware interface
- Django-rendered exam pages
- Legacy proctored exam workflows

---

## JS 2.0: Modern MFE API Approach

### Architecture

The Learning Microfrontend (MFE) fetches exam attempt data via API, which includes the JavaScript worker bundle URL.

### How It Works

1. **MFE requests exam attempt data:**
   ```javascript
   // frontend-lib-special-exams/src/data/api.js
   const attemptData = await fetchExamAttemptsData(courseId, sequenceId);
   ```

2. **API response includes worker URL:**
   ```python
   # edx_proctoring/api.py (get_exam_attempt_data)
   attempt_data = {
       'desktop_application_js_url': provider.get_javascript(),
       'ping_interval': provider.ping_interval,
       'attempt_code': attempt['attempt_code'],
       ...
   }
   ```

3. **MFE extracts URL from response:**
   ```javascript
   // frontend-lib-special-exams/src/data/thunks.js
   const {
       desktop_application_js_url: workerUrl,
       attempt_id: attemptId,
       external_id: attemptExternalId,
   } = activeAttempt || {};
   ```

4. **MFE creates worker dynamically:**
   ```javascript
   // frontend-lib-special-exams/src/data/messages/handlers.js
   const useWorker = window.Worker && activeAttempt && workerUrl;
   
   if (useWorker) {
       workerPromiseForEventNames(
           actionToMessageTypesMap.start, 
           workerUrl
       )(startIntervalInMilliseconds, attemptExternalId)
   }
   ```

### Configuration Requirements

**Build-Time:**
- Same as JS 1.0 (webpack must build worker bundles)
- Worker bundles must be available at known URLs

**Runtime:**
- API endpoints must be accessible
- Backend must return `desktop_application_js_url` in responses
- No template context required

### Used By

- Learning MFE (frontend-app-learning)
- frontend-lib-special-exams library
- Modern exam workflows with API-driven UIs

---

## Build-Time vs Runtime Configuration

### What Happens at Build Time

1. **Django app initialization** (when `manage.py` runs):
   ```python
   # edx_proctoring/apps.py
   def ready(self):
       # Loads all configured backends
       self.backends = {}
       for extension in ExtensionManager(namespace='openedx.proctoring'):
           self.backends[name] = extension.plugin(**options)
       
       # Generates workers.json
       make_worker_config(
           list(self.backends.values()), 
           out=os.path.join(settings.ENV_ROOT, 'workers.json')
       )
   ```

2. **workers.json generation**:
   ```python
   # edx_proctoring/apps.py
   def make_worker_config(backends, out='/tmp/workers.json'):
       if not getattr(settings, 'NODE_MODULES_ROOT', None):
           return False
       
       config = {}
       for backend in backends:
           package = backend.npm_module  # e.g., 'edx-proctoring-proctortrack'
           package_file = os.path.join(
               settings.NODE_MODULES_ROOT, 
               package, 
               'package.json'
           )
           with open(package_file, 'r') as f:
               package_json = json.load(f)
           main_file = package_json['main']
           config[package] = [
               'babel-polyfill',
               os.path.join(settings.NODE_MODULES_ROOT, package, main_file)
           ]
       
       with open(out, 'wb+') as outfp:
           outfp.write(json.dumps(config).encode('utf-8'))
   ```

3. **Webpack consumes workers.json**:
   ```javascript
   // edx-platform/webpack.common.config.js
   var workerConfig = function() {
       try {
           return {
               webworker: {
                   entry: require('../workers.json'),  // <-- reads the file
                   output: {
                       filename: '[name].js',
                       path: path.resolve(__dirname, 'common/static/bundles')
                   },
                   plugins: [
                       new BundleTracker({
                           filename: 'webpack-worker-stats.json'
                       }),
                       new webpack.DefinePlugin({
                           'process.env.JS_ENV_EXTRA_CONFIG': 
                               JSON.parse(process.env.JS_ENV_EXTRA_CONFIG)
                       })
                   ]
               }
           };
       } catch (err) {
           return {};  // Silently returns empty if workers.json missing!
       }
   };
   ```

4. **Webpack builds bundles** and creates `webpack-worker-stats.json`

### What Happens at Runtime

1. **Backend looks up bundle URL:**
   ```python
   # Uses django-webpack-loader
   bundle_chunks = get_files(package, config="WORKERS")
   js_url = bundle_chunks[0]["url"]
   ```

2. **URL is served via:**
   - **JS 1.0:** Template context variable `{{ backend_js_bundle }}`
   - **JS 2.0:** API response field `desktop_application_js_url`

3. **Frontend loads the worker** from the URL

---

## Key Differences Summary

| Aspect | JS 1.0 (Legacy) | JS 2.0 (MFE) |
|--------|-----------------|--------------|
| **Frontend** | Django templates | React MFE |
| **Data Flow** | Template context | REST API |
| **Worker URL Location** | Template variable | API response field |
| **JS Variable** | `edx.courseware.proctored_exam.configuredWorkerURL` | `desktop_application_js_url` |
| **Template Files** | `ready_to_start.html`, `ready_to_submit.html` | N/A |
| **Build Requirements** | Same | Same |
| **Runtime Config** | Template context required | API response required |
| **Modern/Legacy** | Legacy (but still supported) | Modern (recommended) |

### Important Notes

1. **Both approaches share the same build process** - they both need:
   - `workers.json` generated by Django
   - Webpack worker bundles built
   - `webpack-worker-stats.json` created

2. **The worker JavaScript is the same** - only the delivery method differs

3. **Both can coexist** - LMS templates use JS 1.0, MFE uses JS 2.0

4. **Neither eliminates build-time configuration** - the JS bundle must be built at webpack time

---

## Critical Understanding

**The terms "JS 1.0" and "JS 2.0" do NOT refer to:**
- Different versions of the proctoring JavaScript code
- Different webpack configurations
- Different build processes

**They refer ONLY to:**
- How the frontend obtains the worker bundle URL
- Whether it's embedded in templates (1.0) or returned via API (2.0)

**Both approaches require the same build-time steps:**
1. Django must generate `workers.json`
2. Webpack must build worker bundles
3. `webpack-worker-stats.json` must be created
4. Worker bundles must be available at known URLs

The difference is purely in **how the URL is delivered to the frontend at runtime**.

---

## See Also

- [workers.json Generation Requirements](./workers_json_requirements.md)
