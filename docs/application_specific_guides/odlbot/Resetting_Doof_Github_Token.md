# Resetting odlbot / Doof's Github Access Token

## Note: This doc makes lots of assumptions about prior knowledge. TODO :)

From time to time we need to go through the fire drill of rotating all our github access
tokens.

If you need to reset  Doof's you'll need to login to gtihub with the mitx-devops@mit.edu
account.

You can get the 2FA code from Vault in the platform-secrets github secret.

Find the personal access token once logged in by clicking the account icon in the top right,
then choosing Settings -> Developer Settings -> Personal Access Tokens (Classic)

Doof actually gets deployed to heroku. log in to heroku.com with the mitx-devops account.

You can find user, pass and 2FA in vault under platform-secrets/heroku.

Once logged in, click the odl-release-bot application. Then click Settings and navigate to
"Reveal Config Vars".

Now use the web form to edit the value of the GITHUB_ACCESS_TOKEN variable. Replace its
current contents with the new token you just generated on the Github site.

That's it! Doof should be back in no time :)
