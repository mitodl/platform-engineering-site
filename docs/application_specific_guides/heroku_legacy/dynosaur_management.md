# Heroku Dynosaur Management

## Pipeline
The pipeline can be found [here](https://cicd.odl.mit.edu/teams/infrastructure/pipelines/misc-heroku-dyno-management).
And the pipeline definition can be found [here](https://github.com/mitodl/ol-infrastructure/tree/main/src/ol_concourse/pipelines/infrastructure/heroku/pipeline.py).

There are two dicts in the pipeline definition which define the various production and QA applications. The definition of each includes the name of the application as the key to the dict, and a substructure that lists the application owner and a list of dyno name/qty/size combinations. The owner is needed to perform an apiKey lookup from pre-existing SOPS data within the repo.

At the moment we are not resetting the web node counts / configurations because HireFire has a hand in managing those.
