# Resetting Doof (odl-release-bot) npmjs Publish Token

The token Doof uses to publish to npm is stored in the odl-release-bot Heroku app's Configuration under NPM_TOKEN.

You can find the current token in Vault production under platform-secrets under the "npmjs" key.

The npmjs.com login the token is under is mitx-devops. You can find the username, password and TOTP token under that
same vault key.

The token only lasts 3 months and will need to be refreshed.
