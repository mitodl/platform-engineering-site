# OL Secrets Management

The Engineering group in Open Learning hosts its own Hashicorp Vault clusters to handle secrets management. Part of our work is to provide OL developers access to Vault QA to perform the following tasks:
1. Securely share secrets
2. Generate local .env file for app development 

## Requirements
- A Keycloak account in the `ol-platform-engineering` realm. If you currently do not have one, please ping someone in Platform Engineering to set you up.

## 1. Securely share secrets
- Log in to [Vault QA](https://vault-qa.odl.mit.edu)
    - Method: `OIDC`
    - Role: `local-dev`
    * Note: Make sure to enable popups

You should see a popup asking for your Keycloak username and password. Once successfully authenticated, you should see the Vault UI where we have configured a separate Vault mount `secret-sandbox` that should be used for securely sharing sensitive data with the group.

```WARNING - DO NOT store anything permanent in that mount as there are no guarantees that they will not be deleted or overwritten. Any values stored in this mount are visible and accessible by all users of the `ol-platform-engineering` Keycloak realm which as of this writing is and should be restricted to OL Engineering staff.```


## 2. Generate local .env file for app development

- [Install Hashicorp Vault](https://developer.hashicorp.com/vault/tutorials/getting-started/getting-started-install)
- Download the relevant app vars shell script from the repo (Ex. app_vars.sh)
- In your terminal do the following:
    - Set Vault's url as an environment variable
        - `export VAULT_ADDR=https://vault-qa.odl.mit.edu`
    - Login to Vault from the CLI:
        - `vault login -method=oidc role="local-dev"`
    - Run the following to generate vault client config:
        ```
        vault agent generate-config -type="env-template" \
        -exec="./app_vars.sh" \
        -path="secret-dev/*" \
        -path="secret-operations/mailgun" \
        -path="secret-operations/global/embedly" \
        -path="secret-operations/global/odlbot-github-access-token" \
        -path="secret-operations/global/mit-smtp" \
        -path="secret-operations/global/update-search-data-webhook-key" \
        -path="secret-operations/sso/mitlearn" \
        -path="secret-operations/tika/access-token" \
        agent-config.hcl
        ```
    - Start the vault agent:
        - `vault agent -config=agent-config.hcl -log-level=error`

You should now have a .env file containing the secrets for the relevant app from vault.


### References
- https://developer.hashicorp.com/vault/docs/agent-and-proxy/agent/generate-config

## Bonus Note : Generating IAM creds for MIT Learn local development

Apparently Devs sometimes need valid IAM credentials for local development with MIT Learn. Previously people were just lifting these creds out of Heroku settings but that isn't an option now. To replace that, use the following link:

https://vault-qa.odl.mit.edu/ui/vault/secrets/aws-mitx/credentials/ol-mitopen-application

You will need to login with a classic github token that has `read:org` permissions. This link will allow you to generate IAM creds that last 32 days and are personal to just you rather than shared ones from the app itself. 

