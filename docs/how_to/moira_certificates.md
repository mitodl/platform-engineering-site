# Moira Certificates

There are two services in our porfolio that interact with [Moira](https://ist.mit.edu/email-lists).

1. MIT Open / OpenDiscussions
2. ODL-Video-Service

Both of these services authenticate against Moira with certificates issued by [ca.mit.edu](https://ca.mit.edu/ca/) which is also the provider of MIT Personal Certificates. There is no web interface for requesting an application certificate from ca.mit.edu, so you need to email mitcert@mit.edu with the CSR in the body of the email and a clear request that you're asking for a certificate issued from ca.mit.edu and NOT InCommon/Internet2 which is where most MIT certificates now come from.

Both of these applications utilize the same two environment variables for storing and accessing this key/cert pair.

- **MIT_WS_CERTIFICATE**
- **MIT_WS_PRIVATE_KEY**

## Generating a CSR From the MITWS Private Key

This is the OpenSSL invocation and details I used to generate the CSR for the OVS cert:

```
╭─feoh at prometheus in ~/Packages/openssl 25-04-07 - 15:22:04
╰─○ openssl req -out app.csr -key mitws.key -new -sha256                                                                                                                                          <region:us-east-1>
You are about to be asked to enter information that will be incorporated
into your certificate request.
What you are about to enter is what is called a Distinguished Name or a DN.
There are quite a few fields but you can leave some blank
For some fields there will be a default value,
If you enter '.', the field will be left blank.
-----
Country Name (2 letter code) [AU]:US
State or Province Name (full name) [Some-State]:Massachusetts
Locality Name (eg, city) []:Cambridge
Organization Name (eg, company) [Internet Widgits Pty Ltd]:MIT
Organizational Unit Name (eg, section) []:odl-video
Common Name (e.g. server FQDN or YOUR name) []:video.odl.mit.edu
Email Address []:odl-devops@mit.edu

Please enter the following 'extra' attributes
to be sent with your certificate request
A challenge password []:
An optional company name []:
```

## MITOpen Vault Locations

- In all vault environments: `secret-mit-open/global/mit-application-certificate`
- Maintained by hand.

## ODL Video Service Vault Location

- In all vault environments: `secret-odl-video-service/ovs/secrets`
  - Inside a single JSON structure at `misc.mit_ws_certificate` and `misc.mit_ws_private_key`
- Maintained automatically by pulumi.
  - `sr/bridge/secrets/odl_video_service` or [here](https://github.com/mitodl/ol-infrastructure/tree/main/src/bridge/secrets/odl_video_service)


## Certificate Usage and Expiration Tracking

| Action Date | Application | Description | Who |
|-------------|-------------|-------------|-----|
| 20230625    | Open        | Replaced MIT Open certificate, expires 20240625 | MD |
| 20230928    | OVS         | OVS Cert expired, replaced with Open certificate above, expires 20240625 | MD |
| 20240201    | Both        | No action. Verified certificates currently in use. Updated reminder in team calendar. | MD |
| 20240613    | Both        | Replaced both certificates with 2024-2025 versions. Reminder sent to team calendar. | MD |
