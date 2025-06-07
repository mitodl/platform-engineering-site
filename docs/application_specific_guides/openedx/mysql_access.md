# Querying An MIT OL Open EdX Mysql Database

This is a quick and dirty guide to connecting to the OpenEdX MySQL database for
one of our products.

## Connect to an EC2 server that hosts containers for the product in question

For instance, in the case of XPro CI, connect to a server in instance group
edxapp-[web/worker]-mitxpro-ci.

You can find detailed instructions on how to do this
[here](access_django_manage.md).

## Install a mysql or mariadb client if one's not there already

(If you do this in production environments, and you probably shouldn't, be sure
to remove it when done.)

```
sudo apt install mariadb-client
```
OR

```
sudo apt install mysql-client
```
## Get the Database Credentials

Use docker compose to connect to a container like the LMS or CMS:

```
docker compose exec -it lms bash
```

and then, once insde the container, you can find the database connection
information in /openedx/edx-platform/lms/envs/lms.yaml in the DATABASES section.

Be sure to choose the correct database for your environment.

## To The Prompt!

Now, Ctrl-D out of the container bash you were logged into and get back to the
host you sshed into.

You can now use the mysql client to connect to the database.

e.g.

```
mysql -h <hostname> -u <username> -p
```

You'll need to enter or paste in the password you found in the previous section
when prompted.

That should be all you need to get a mysql prompt to run queries against! Be
careful, there are no guardrails here!
