## Configure a Log Drain

To get logs from heroku applications -> Grafana we need to configure a 'log drain' in heroku for each application. This is pretty straight forward but does require collecting a few pieces of information first:

- The address of the 'vector-log-proxy'
  - log-proxy-ci.odl.mit.edu
  - log-proxy-qa.odl.mit.edu
  - log-proxy.odl.mit.edu
- The basic auth password for the 'vector-log-proxy' server.
  - `sops -d src/bridge/secrets/vector/vector_log_proxy.ci.yaml`  heroku section, username: vector-log-proxy
  - `sops -d src/bridge/secrets/vector/vector_log_proxy.qa.yaml`  heroku section, username: vector-log-proxy
  - `sops -d src/bridge/secrets/vector/vector_log_proxy.production.yaml`  heroku section, username: vector-log-proxy

Next we configure the log drain using the heroku-cli. There is no web interface for configuring this.

```
heroku drains:add -a <HEROKU_APP_NAME> 'https://vector-log-proxy:<PASSWORD_FROM_SOPS>@<URL_FROM_ABOVE>:9000/events?app_name=<APP_NAME_WO_ENV_INFO>&environment=<ENV>&service=heroku'
```

And you'll get a response like: 

```
Successfully added drain https://vector-log-proxy:<The rest of the URL you just used>
```

`app_name`, `environment`, and `service` all refer directly to the organization fields used to categorize the logs in Grafana.

## References

https://devcenter.heroku.com/articles/logplex
https://devcenter.heroku.com/articles/log-drains#https-drains
