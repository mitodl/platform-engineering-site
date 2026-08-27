# New Projects

When starting a new project, we have a baseline of what's necessary
from an infrastructure perspective. Here's a checklist:

- [ ] Do you have a README?
- [ ] Can you run the tests for your code? Is that documented in the README?
- [ ] Do you have docker setup for local development?
- [ ] Do you have a LICENSE file?
- [ ] Are the tests running on a CI server like Travis?
- [ ] Do you have relevant linters setup for the languages you're using?
- [ ] Are Python dependencies managed with [`uv`](https://docs.astral.sh/uv/) (`pyproject.toml` + a committed `uv.lock`)?

READMEs for your project.

- [ ] Does it include how to install the app?
- [ ] Does it include how to run the tests?
- [ ] Does it contain a build status or code coverage badge?
- [ ] Does it link to relevant documents?
- [ ] Does it mention the software license used?

For Django projects specifically..

- [ ] Does it use the same database backend locally as it will in production?
- [ ] Does it support the current and previous Python minor versions (as of writing: 3.14 and 3.13)? Our existing projects vary widely (3.11 through 3.14), so this is guidance for new projects, not a description of the status quo - check [python.org's supported-versions table](https://devguide.python.org/versions/) for the current answer rather than trusting this specific pair indefinitely.
- [ ] Does it run mypy & ruff as linters?
