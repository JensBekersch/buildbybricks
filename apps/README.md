# App Instances

Each subfolder can define one reusable application instance.

```text
apps/
  policy-assistant/
    app_profile.json
    evaluation_cases.json
```

Knowledge for that instance lives under:

```text
data/<app_id>/<collection>/
```

The legacy template remains available as the `default` application.
