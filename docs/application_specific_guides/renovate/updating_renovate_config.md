# Validating Renovate Configuration Changes

You can find our Renovate configuration in the .github repository at the root of
our mitodl organization
[here](https://github.com/mitodl/.github/blob/main/renovate-config.json).

You can validate any changes you make by running the following `npx` command.
(This requires a working node.js installation):
```
npx --package renovate renovate-config-validator
```

This will surface any errors you may have made, and if all is well you'll see a
message like:

```
─cpatti at rocinante in ~/src/mit/.github on main✔ 25-09-24 - 16:46:22
╰─⠠⠵ npx --package renovate renovate-config-validator                                                      <region:us-east-1>
 INFO: Validating renovate.json
 INFO: Config validated successfully
 ```
