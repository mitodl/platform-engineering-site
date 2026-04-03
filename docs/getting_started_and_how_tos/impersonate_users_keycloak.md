# Impersonating Users in Keycloak

/// admonition | Tip
    type: warning

Be careful impersonating users! Do not take unnecessary actions on their behalf.

- Use a separate browser profile to help ensure you know which user you are using.
- Log out of the user's account when you're done.
///

1. Log in to the Keycloak Admin Console, https://sso.ol.mit.edu/admin/olapps/console/
    - As Devops for access.
2. Select the Users tab on left navigation.
3. Search for the user you want to impersonate.
4. Click the user's username to navigate to the user detail view.
5. From the "Action" dropdown in to-left, select "Impersonate".
    - We use a single realm, so this will limit your access to the admin console in your current browser session.
