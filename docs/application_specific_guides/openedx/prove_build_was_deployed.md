# Proving That A Particular OpenEdX Build Was Deployed To a Product Environment

This doc is *NOT* exhaustive. It assumes prior knowledge of our products and
EC2. I can fill in the exhaustive details later if there's ever time :)

There are two methods for determining this.

## AMI

- Find the instance in the AWS console. For instance if looking for an XPro CI
instance, use `edxapp-web-xpro-ci` to find an XPro CI webserver. Select it.
- Click "AMI" an select the instance's AMI image.
- Under the "Tags" tab one of the tags is `edx_sha`. That's the Git repository hash
this container is built from.

## Container Contents

- Log onto the EC2 instance you want to check.
- Get a shell inside an LMS/CMS container e.g.
```
cd /etc/docker/compose
sudo -s
docker compose exec -it cms bash
```
- Once inside you can change directory to /openedx/edx-platform and run `git
log`. That will show you the commit that built the container.
