# Inviting New users To Keycloak Domains

## Getting Access to Keycloak Admin Console

### Get The Creds

Browse to [Vault Production](https://vault-production.odl.mit.edu) and be sure you can login successfully with your
Github token.

Once you've done that, navigate to the [Keycloak
Secret](https://vault-production.odl.mit.edu/ui/vault/secrets/secret-keycloak/kv/keycloak-secrets/details?version=1) and
copy out the admin username (Psst. It's just admin) and admin password.

### To The Admin Console!

Now browse to the [Keycloak Admin
Console](https://sso.ol.mit.edu/realms/master/protocol/openid-connect/auth?client_id=security-admin-console&redirect_uri=https%3A%2F%2Fsso.ol.mit.edu%2Fadmin%2Fmaster%2Fconsole%2F&state=4cd72daa-ed0a-434d-a953-56e352809416&response_mode=query&response_type=code&scope=openid&nonce=5dbae732-e882-42a2-854e-3a9e1207ab8e&code_challenge=AiGAUtPNSYmDIz2TVo0yUbb8SNbRFzuD3Ex7aDz7bPI&code_challenge_method=S256)
and use the credentials we fetched in the previous step to login.

You should now see a "Welcome to Keycloak!" page. You're in!

### Actually Inviting The Users

First, navigate to the domain you want to invite users to.

Click the hamburger menu (Square with three lines) in the upper right, and click "Manage Realms".

Now click the realm you want to invite users to, say "ol-platform-engineering".

Again, go back to the hamburger menu and click "Organizations". Choose the relevant one.
(Probably MIT or Arbisoft for employees of those orgs, respectively.)

You'll see an "Invitations" tab under "Members". Click that and then click "Invite Member".

Enter their first name, last name and correct E-mail in the dialog, click Submit, and you'll see
a notification about the invite being sent. You're done!
