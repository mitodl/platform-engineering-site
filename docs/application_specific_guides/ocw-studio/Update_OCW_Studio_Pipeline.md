# Updating the OCW Studio Pipeline

## Make Your Change

In this case, we needed to pin the
aws-cli container to a previous
version because Amazon upgraded it
from AL2 to AL2023 out from underneath
us. The PR is
[here](https://github.com/mitodl/ocw-studio/pull/2624).

Get your PR approved.

## Allow Doof To Enact His Evil Plan

Send the message `@doof release notes`
to [this slack
channel](https://mit.enterprise.slack.com/archives/G01JPJZQX8E).

Doof will prompt you to click your
checkboxes for this release. It takes
a bit for him to notice your change.

Click the check box, and wait another
bit while he 'sees' that. Then, when
prompted, tell Doof to merge your
change and deploy the Heroku app.

When Doof is done the output should
look something like:

```

Dr. Heinz Doofenshmirtz
APP  10:53 AM
My evil scheme v0.153.2 for ocw-studio has been released to production at https://ocw-studio.odl.mit.edu. And by 'released', I mean completely...um...leased.
```

## Update The Pipeline

Access a shell on Heroku RC by
running:

```
heroku run --app ocw-studio-rc bash

```


Once you get a shell prompt, run the
following command:

`./manage.py backpopulate_pipelines -f
ocw-www`

You may omit the -f ocw-www to update
all pipelines.

The output should look something like:

```
~ $ ./manage.py backpopulate_pipelines
Creating website pipelines
Started celery task ad65adf1-7f8b-4f80-8c44-9ddebe329bca to upsert pipelines for 2859 sites
Waiting on task...
Pipeline upserts finished, took 422.49245 seconds
~ $
```

## Re-trigger The Failed Pipeline

Surf to [The OCW Studio Pulumi Pipeline](https://cicd.odl.mit.edu/teams/infrastructure/pipelines/pulumi-ocw-studio) and trigger a new build.

That should be it! Assuming your
changes worked, the pipeline should
now succeed. If it doesn't but you're
sure your changes are correct, ensure
that Doof actually finished deploying.
