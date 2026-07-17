# Web App Guide

# Docker/Django/Webpack Web App Guide

**SECTIONS**
1. [Initial Setup](#initial-setup)
1. [Running and Accessing the App](#running-and-accessing-the-app)
1. [Testing and Formatting](#testing-and-formatting)
1. [Administering your Local App](#administering-your-local-app)
1. [Troubleshooting](#troubleshooting)


# Initial Setup

### Major Dependencies
- Docker
  - _[MacOS only]_ We use **Docker Desktop**&#42;, a desktop development environment that includes Docker.  
    Recommended MacOS install method: [Download from Docker website](https://docs.docker.com/desktop/setup/install/mac-install/)
- docker-compose
  - If you've installed Docker Desktop, you already have `docker-compose` installed. 
  - If not you may need to install it separately.
    - Recommended install: pip (`pip install docker-compose`)

### Build And Configure Docker Containers

All commands in this guide should be run from the root directory of your project's repository (unless specified otherwise).

#### 1) Create your ``.env`` file

    cp .env.example .env

The `.env.example` file contains settings variables for which you will need to provide values in order to run the
app. Sometimes default values are given. To get a better idea about what values are needed, refer to the specific
project's README file.

#### 2) Build the containers

    docker-compose build

*NOTE: You will also need to run this command whenever requirements files change (``requirements.txt``, ``test_requirements.txt``, etc.)*

#### _(Optional)_ Create a superuser
Some of our apps include user creation as part of their specific setup steps. If the given app does not
include steps to create a user, you can create one easily via Django's `createsuperuser` command.
It will prompt you for the username and some other details for this user.

    docker-compose run web ./manage.py createsuperuser

### Add `/etc/hosts` alias for the site

There are two scenarios where this will be needed:

1. Multiple locally-running apps need to share a cookie (e.g.: MicroMasters and Open Discussions).
1. You are an MacOS user. Due to networking differences between Docker for Mac and standard Docker, locally running apps can only communicate
with each other in MacOS if `/etc/hosts` aliases are created for each app.

Our established pattern is to use `odl.local` as the domain. The `/etc/hosts` entry for a locally-running site will look like this:

```
127.0.0.1       <site_abbreviation>.odl.local

# Example: for Micromasters...
127.0.0.1       mm.odl.local
# Example: for open-discussions...
127.0.0.1       od.odl.local
```

# Running and Accessing the App

#### 1) Run the containers

Start all the services that are required to run the app:

    docker-compose up

*NOTE: In most repos this will also apply migrations. Consult your docker-compose.yml file to see what specific actions are taken*

#### 2) Navigate to the running app in your browser

Your app should now be accessible via browser:

1. The URL of the locally-running site needs to include the port number that the `nginx` service is running on.
    - One-line command to figure out that port number: `docker-compose ps nginx | perl -nle '/[0-9\.]*:(\d+)/ && print "$1";'`
    - This port number is specified for the `nginx` service in `docker-compose.yml`
1. _[Linux only]:_ Navigate to `localhost:PORT` (e.g.: `localhost:8079`)
1. _[MacOS only]:_ Navigate to `ETC_HOSTS_ALIAS:PORT` (e.g.: `mm.odl.local:8079`). Like Linux users, you _can_ navigate to `localhost:PORT` (e.g.: `localhost:8079`) to use the
  locally-running site, but it's recommended/essential that you add an `/etc/hosts` alias and use that URL instead.
  More info on that in the section above.


# Testing and Formatting

There are a few different commands for running tests/linters and formatting code.

*NOTE: The `--rm` option for the `docker-compose run` command tells Docker to destroy the container after it finishes running. This is useful for running specific commands in one-off containers. This prevents the accumulation of unused Docker containers on your machine.*

### Python tests, linting, and formatting

We use `pytest` (with various plugins) to run our Python test suite in most of our projects.

#### With `pytest`...
```bash
# Run Python tests with linting
docker-compose run --rm web pytest
# Run Python tests in a single file
docker-compose run --rm web pytest /path/to/test.py
# Run Python test cases in a single file that match some function/class name
docker-compose run --rm web pytest /path/to/test.py -k test_some_logic
# Run Python tests without linter, without coverage report, and without log capture
docker-compose run --rm web pytest --no-cov --no-pylint --show-capture=no
# Some of our projects allow you to pass in a single flag to run tests only (no linter, cov report, or log capture)
docker-compose run --rm web pytest --simple

### Linting
# If the pytest-pylint is NOT installed (check test_requirements.txt), run pylint directly
docker-compose run --rm web bash -c "pylint ./**/*.py"
# If the pytest-pylint IS installed, run the pylint via pytest
docker-compose run --rm web pytest --pylint -m pylint
```

#### Formatting
Most of our projects use the `black` formatter to enforce certain formatting rules. This should be run before any commit that makes changes to Python code (ignore this if your project does not list `black` in the `test_requirements.txt`).
Additionally, many of our projects perform formatting as a part of their `pre-commit` hook, so if you have that hook installed it will automatically run formatting checks on commit.

```bash
# Format all Python files in the repo
docker-compose run --rm web black .
# Format a specific file
docker-compose run --rm web black /path/to/file.py
```

#### Import sorting
Some of our projects include [`isort`](https://pypi.org/project/isort/) to automatically sort Python imports. If your project uses `isort` and requires sorted imports as a part of the build, that package will be included in `test_requirements.txt`

```
# Sort all imports 
docker-compose run --rm web bash -c "isort ."
# Check to see if imports are sorted
docker-compose run --rm web bash -c "isort -c ."
```

#### Speeding up test development
There are many scenarios where you'll want to run tests many times in a row (authoring new tests, fixing old tests and checking if they pass). In that case it will save time to run a bash shell in a new container and run these commands as needed in that container.

```bash
# On host machine...
docker-compose run --rm web bash
# On the bash prompt inside the new container
pytest /path/to/test.py
```

### JS/CSS tests, linting, formatting, and type-checking

#### Running tests via helper script

Most of our projects include a helper script to run JS tests. 

If your project includes `/scripts/test/js_test.sh` or `/js_test.sh`, this is how you can run the JS test suite:

```bash
docker-compose run --rm watch ./scripts/test/js_test.sh
# Run JS tests in specific file
docker-compose run --rm watch ./scripts/test/js_test.sh path/to/file.js
# Run JS tests in specific file with a description that matches some text
docker-compose run --rm watch ./scripts/test/js_test.sh path/to/file.js "should test basic arithmetic"
```

**NOTE:** 
In some of our projects we include a shell script that runs the entire test suite including linting, etc.: `./test_suite.sh`.
If you're in yarn workspaces enabled project e.g. MITxOnline, you will need to replace `yarn run` with `yarn workspaces foreach run` for the below commands.


#### Running tests via yarn

In 2021 we changed our JS testing practice to use yarn directly to run the JS test suite, and to use [jest](https://jestjs.io/docs/getting-started) 
as our testing framework.

If your project DOES NOT include a `js_test.sh` file, this is how you can run the JS test suite:

```bash
docker-compose run --rm watch yarn run test
# Run JS tests in specific file
docker-compose run --rm watch yarn run test path/to/file.test.js
# Run JS tests in specific file with a description that matches some text
docker-compose run --rm watch yarn run test path/to/file.test.js -- -t "should test basic arithmetic"

# Run jest in watch mode (`jest --watch`) to continuously catch test failures
docker-compose run --rm watch yarn run test:watch
# Generate a coverage report
docker-compose run --rm watch yarn run test:coverage
```

#### Linting and formatting
Many of our projects perform formatting as a part of their `pre-commit` hook, so if you have that hook installed it will automatically run formatting checks on commit.

```bash
# Run the JS linter
docker-compose run --rm watch yarn run lint
# Run SCSS linter
docker-compose run --rm watch yarn run scss_lint
# Run prettier-eslint, which fixes style issues that may be causing the build to fail
docker-compose run --rm watch yarn run fmt
```

#### Type-checking

If your project has files with the extension `.ts`/`.tsx`, your project is 
Typescript-enabled.

**Typescript** 

As stated above, type-checking is done automatically with Typescript-enabled projects, so it's not necessary to run
any commands, but you can still type-check with a command if you prefer:

```bash
docker-compose run --rm watch yarn run typecheck
```

This runs `tsc --noEmit`, which basically type-checks the program and outputs
any error but does not run a full compilation. We have incremental compilation
turned on, so this should be relatively fast. It uses a file called
`.tsbuildinfo` for incremental compilation.

Most of our legacy projects use [Flow](https://flow.org/en/docs/) 
type-checking. We switched to Typescript for new projects in 2021. Type-checking only needs to be invoked directly 
in our projects that use Flow. 

**Flow**

```bash
# Run the Flow type checker to check for typing errors
docker-compose run --rm watch yarn run-script flow
```

#### Speeding up test development
You can speed up JS test development in the same way described in the Python testing section above by starting the
`watch` container instead of the `web` container.


# Administering your Local App

#### Running a Django shell

    docker-compose run --rm web ./manage.py shell

# Troubleshooting

#### Error message indicating that the `auth_user` table doesn't exist

Try running `docker-compose run web ./manage.py migrate auth`, then run `docker-compose run web ./manage.py migrate`.

#### _[MacOS only]_ Error indicating that Docker for Mac is not running (even though it is running)

Open a new terminal tab/window, navigate to the same directory, and re-run the same command (e.g.: `docker-compose up`). For whatever reason, a terminal window can sometimes fail to recognize that Docker for Mac is running, and a fresh terminal window will fix that.
