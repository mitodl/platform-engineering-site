## Overview
This document provides guidance for configuring single sign-on (SSO) with our platform using either OpenID Connect (OIDC) or SAML protocols. This integration allows your users to access our services using their existing organizational credentials from any compatible identity provider.

### Quick Navigation
- [Prerequisites](#prerequisites)
- [Protocol Selection](#protocol-selection)
- [General Configuration Requirements](#general-configuration-requirements)
- [Required Information Collection](#required-information-collection)
- [Information to Provide Our Team](#information-to-provide-our-team)
- [Configuration Exchange Process](#configuration-exchange-process)
- [Testing the Integration](#testing-the-integration)
- [Next Steps](#next-steps)
- [Support](#support)
- [Provider-Specific Examples](#provider-specific-examples)
  - [Microsoft Entra ID (Azure AD) - OIDC](#microsoft-entra-id-azure-ad---oidc)
  - [Microsoft Entra ID (Azure AD) - SAML](#microsoft-entra-id-azure-ad---saml)

## Prerequisites
- Administrative access to your identity provider (IdP)
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
- **Supported by**: Most modern identity providers

### Alternative: SAML 2.0
- **Best for**: Enterprise applications, legacy system integration
- **Advantages**: Mature protocol, extensive enterprise support
- **Setup complexity**: Medium to High
- **Supported by**: All major enterprise identity providers

## General Configuration Requirements

### OIDC Configuration Requirements
Your identity provider will need to be configured with the following settings:

**Application Registration Details:**
- **Application Name**: `MIT Learn` (or your preferred name)
- **Redirect URI**: `https://sso.ol.mit.edu/realms/olapps/broker/oidc/endpoint`
- **Response Type**: `code`
- **Grant Type**: `authorization_code`

**Required Claims/Scopes:**
- `openid` (Sign users in)
- `profile` (View users' basic profile)
- `email` (View users' email address)

**Authentication Method:**
- Certificate-based authentication using the public certificate provided by our team

### SAML Configuration Requirements
Your identity provider will need to be configured with the following settings:

**Service Provider (SP) Details:**
- **Entity ID**: `https://sso.ol.mit.edu/realms/olapps`
- **URLs**: Will be provided by our team after initial configuration

**Required Attributes:**
- **Name ID Format**: Email address
- **Email**: User's email address
- **Given Name**: User's first name
- **Surname**: User's last name
- **Display Name**: User's full display name

**Certificate Configuration:**
- **Signing Algorithm**: SHA-256
- **Response Signing**: Required

## Required Information Collection

### For OIDC Integration
Please collect the following information from your identity provider:
- **Client ID**: Your application's unique identifier
- **OpenID Connect Discovery URL**: Usually `https://[your-idp]/.well-known/openid-configuration`
- **Tenant/Domain Information**: If applicable to your provider

### For SAML Integration
Please collect the following information from your identity provider:
- **Federation Metadata URL**: If available (recommended - contains all configuration details below)

**OR if metadata URL is not available, provide these individual items:**
- **Identity Provider Entity ID**: Your IdP's unique identifier
- **Single Sign-On URL**: Where users are redirected for authentication
- **Single Logout URL**: Where users are redirected for logout
- **X.509 Certificate**: Your IdP's signing certificate
- **Federation Metadata URL**: If available (optional but recommended)

## Information to Provide Our Team

Please fill out the following Google Form with your configuration details: [LINK_TO_GOOGLE_FORM]

**Important**: Include all the information gathered in the [Required Information Collection](#required-information-collection) section above.

## Configuration Exchange Process

After you submit your information:

1. **Our team will configure your organization** in our system and provide you with:
   - Public certificate for authentication (OIDC and SAML)
   - Organization-specific endpoints (SAML only)
   - Service Provider metadata file (SAML only)

2. **You will need to update your identity provider** with the information we provide

3. **Testing can begin** once both sides have completed their configuration

**Note**: SAML configurations require additional endpoint information from our team before you can complete your setup.

## Testing the Integration

**Note**: Testing can only be performed after the configuration exchange process above is complete.

### Test User Setup
1. Create a test user in your identity provider
2. Ensure the test user has the required attributes (email, name, etc.)
3. Assign the test user access to the MIT Learn application

### Testing Steps
1. Navigate to our platform's login page
2. Click "Log in"
3. Enter the email address for your test user
4. Click Next
5. You should be redirected to your identity provider for authentication
6. Enter your credentials at your identity provider
7. After successful authentication, you will be logged into the Learn web site
8. Confirm the test user's name and information on the Profile page at https://learn.mit.edu/dashboard/profile

### Common Troubleshooting

#### OIDC-specific Issues
- **Invalid redirect URI**: Verify the reply URL matches exactly
- **Token validation errors**: Check clock synchronization between systems
- **Missing user attributes**: Verify claim mappings in your identity provider
- **Permission denied**: Ensure users are assigned to the application

#### SAML-specific Issues
- **Invalid SAML Response**: Check certificate validity and signing configuration
- **Attribute mapping errors**: Verify claim names and formats match requirements
- **Invalid destination**: Ensure ACS URL matches exactly
- **Clock skew issues**: Verify time synchronization between systems

## Next Steps

1. Choose your preferred protocol (OIDC recommended)
2. Configure your identity provider using the requirements above
3. Provide the required configuration details to our team via the form
4. Wait for confirmation that our team has completed the configuration
5. Test the integration with a small group of users
6. Schedule a validation call to verify the integration
7. Plan your user rollout and communication strategy

## Support

For technical questions during setup:
- Contact our integration team at: [mitlearn-support@mit.edu](mailto:mitlearn-support@mit.edu)
- Include any error messages or screenshots for faster resolution

For ongoing operational support after go-live:
- Use your standard support channels
- SSO-related issues should include user Principal Name and timestamp

---

## Provider-Specific Examples

The following sections provide detailed, step-by-step instructions for specific identity providers. Use these as reference implementations of the general requirements outlined above.

## Microsoft Entra ID (Azure AD) - OIDC

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
2. Select the **Certificates** tab and click **Upload certificate**
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

## Microsoft Entra ID (Azure AD) - SAML

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

### Security Considerations for Entra ID

#### Conditional Access Policies
Consider implementing Conditional Access policies for additional security:
- Require multi-factor authentication
- Restrict access based on location or device compliance
- Implement risk-based access controls