## Overview
This document provides step-by-step instructions for configuring Microsoft Entra ID (formerly Azure AD) to enable single sign-on (SSO) with our platform using either OpenID Connect (OIDC) or SAML protocols. This integration allows your users to access our services using their existing organizational credentials.

### Quick Navigation
- [Prerequisites](#prerequisites)
- [Protocol Selection](#protocol-selection)
- [OIDC (Microsoft Entra ID) Configuration](#oidc-microsoft-entra-id-configuration)
- [SAML Configuration](#saml-configuration)
- [Security Considerations](#security-considerations)
- [Testing the Integration](#testing-the-integration)
- [Information to Provide Our Team](#information-to-provide-our-team)
- [Next Steps](#next-steps)
- [Support](#support)

## Prerequisites
- Administrative access to your Microsoft Entra ID tenant
- Access to the Azure portal (portal.azure.com)
- The following information will be provided by our team:
  - Keycloak realm URL
  - Keycloak realm public certificate
  - Organization-specific configuration details

## Protocol Selection
We recommend **OpenID Connect (OIDC)** for most implementations due to its modern design and ease of configuration.

### Recommended: OpenID Connect (OIDC)
- **Best for**: Modern applications, mobile apps, API access
- **Advantages**: JSON-based, built on OAuth2, excellent token management
- **Setup complexity**: Low to Medium

### Alternative: SAML 2.0
- **Best for**: Enterprise applications, legacy system integration
- **Advantages**: Mature protocol, extensive enterprise support
- **Setup complexity**: Medium to High

## OIDC (Microsoft Entra ID) Configuration

### Step 1: Create Application Registration in Entra ID
1. Navigate to the Azure portal (portal.azure.com)
2. Go to **Microsoft Entra ID** → **App registrations**
3. Click **New registration**
4. Configure the following settings:
   - **User-facing display name for this application**: `MIT Learn`
   - **Supported account types**: Depends on their setup and what accounts they want to allow
   - **Redirect URI**: Web - `https://sso.ol.mit.edu/realms/olapps/broker/oidc/endpoint`
5. Click **Register**

### Step 2: Configure Application Registration Secrets
1. In your new application, go to **Certificates & secrets**
2. Select **Certificates** -> **Upload certificate**
3. Upload Public certificate provided to you by our team

### Step 3: Configure Application Registration API permissions
1. In your new application, go to **API permissions**
2. Ensure the following Microsoft Graph permissions:
   - `openid` (Sign users in)
   - `profile` (View users' basic profile)
   - `email` (View users' email address)
   - `User.Read` (Sign in and read user profile)

### Step 4: Collect Configuration Details
Gather the following information to provide to our team:
- **Application (Client) ID**: Found in App Registration overview
- **OpenID Connect Metadata URL**: `https://login.microsoftonline.com/[TENANT_ID]/v2.0/.well-known/openid_configuration`
(Note: You can find your **Tenant ID** on the **Overview** page of your Microsoft Entra ID instance in the Azure portal.)

## SAML Configuration

### Step 1: Create Enterprise Application in Entra ID
1. Navigate to the Azure portal (portal.azure.com)
2. Go to **Microsoft Entra ID** → **Enterprise applications**
3. Click **New application**
4. Click **Create your own application**
5. Configure the following settings:
   - **Name**: `MIT Learn`
   - **What are you looking to do with your application?**: Select "Integrate any other application you don't find in the gallery (Non-gallery)"
6. Click **Create**

### Step 2: Configure Basic SAML Configuration
1. In your new enterprise application, go to **Single sign-on**
2. Select **SAML** as the single sign-on method
3. In the **Basic SAML Configuration** section, click **Edit**
4. Configure the following settings:
   - **Identifier (Entity ID)**: `https://sso.ol.mit.edu/realms/olapps`
   - **Reply URL (Assertion Consumer Service URL)**: `https://sso.ol.mit.edu/realms/olapps/broker/saml/endpoint`
   - **Sign on URL**: `https://sso.ol.mit.edu/realms/olapps/broker/saml/endpoint`
   - **Relay State**: Leave blank
   - **Logout URL**: `https://sso.ol.mit.edu/realms/olapps/broker/saml/endpoint`
5. Click **Save**

### Step 3: Configure Attributes & Claims
1. In the **Attributes & Claims** section, click **Edit**
2. Ensure the following claims are present:
   - **Unique User Identifier (Name ID)**: user.userprincipalname
   - **emailaddress**: user.mail
   - **givenname**: user.givenname
   - **surname**: user.surname
   - **name**: user.displayname
3. Set **Name identifier format** to **Email address**
4. Click **Save**

### Step 4: Configure SAML Signing Certificate
1. In the **SAML Certificates** section, note the following:
   - **App Federation Metadata Url**: Copy this URL to provide to our team
   - **Certificate (Base64)**: Download this certificate
   - **Federation Metadata XML**: Download this file
2. In the **Advanced Certificate Settings**, ensure:
   - **Signing Option**: Sign SAML response
   - **Signing Algorithm**: SHA-256

### Step 5: Collect Configuration Details
Gather the following information to provide to our team:
- **Azure AD Identifier (Entity ID)**: Found in the Set up [Application Name] section
- **Login URL**: Found in the Set up [Application Name] section
- **Logout URL**: Found in the Set up [Application Name] section
- **App Federation Metadata URL**: From Step 4
- **Certificate (Base64)**: Downloaded file from Step 4
- **Federation Metadata XML**: Downloaded file from Step 4

## Security Considerations

### Conditional Access Policies
Consider implementing Conditional Access policies for additional security:
- Require multi-factor authentication
- Restrict access based on location or device compliance
- Implement risk-based access controls

## Testing the Integration

### Test User Access
1. Create a test user in your Entra ID tenant
2. Assign them to the application
3. Navigate to our platform's login page
4. Click "Log in"
5. Enter the email address for your test user.
6. Click Next
7. You should be redirected to you MS Entra service. Enter your credentials. 
8. After successful authentication, you will be logged into the Learn web site. Confirm the test user's name on the Profile page at https://learn.mit.edu/dashboard/profile

### Troubleshooting Common Issues

#### OIDC-specific Issues
- **Invalid redirect URI**: Verify the reply URL matches exactly
- **Token validation errors**: Check clock synchronization between systems
- **Missing user attributes**: Verify claim mappings in Entra ID
- **Permission denied**: Ensure users are assigned to the application

#### SAML-specific Issues
- **Invalid SAML Response**: Check certificate validity and signing configuration
- **Attribute mapping errors**: Verify claim names and formats match requirements
- **Invalid destination**: Ensure ACS URL matches exactly
- **Clock skew issues**: Verify time synchronization between systems

## Information to Provide Our Team

Please fill out the following Google Form with your configuration details: [LINK_TO_GOOGLE_FORM]

## Next Steps

1. Complete the configuration steps for your chosen protocol
2. Test the integration with a small group of users
3. Provide the required configuration details to our team
4. Schedule a validation call to verify the integration
5. Plan your user rollout and communication strategy

## Support

For technical questions during setup:
- Contact our integration team at: [mitlearn-support@mit.edu](mailto:mitlearn-support@mit.edu)
- Include any error messages or screenshots for faster resolution

For ongoing operational support after go-live:
- Use your standard support channels
- SSO-related issues should include user Principal Name and timestamp