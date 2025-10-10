# Deployment Notes 

*Note:* This is not meant to be a guide on how to deploy a django app, it just serves as a reference for project maintainers.  

First and foremost, see the [django deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/).

All environment variables must be set, with `SPC_DEBUG=False` (or equivalently unset), and since most hosts will block SMTP traffic, we'll use a email service to send verification emails. The code uses [resend](https://resend.com/) to do this, so we'll need to set the `RESEND_API_KEY` envvar as well. We fall back to django's smtp functionality if the api key is not found (only for use in development). This means the following envvars are unused when in prod: `SPC_EMAILUSER`, `SPC_EMAILPASSWORD`, `SPC_EMAILHOST`. 

# Build commands

See `build.sh`.

# Deploy commands

```
gunicorn spcwebsite.wsgi:application --timeout 120
```

# Dataset backup and restore

```
sqlite3 db.sqlite3 ".backup backup.db"
sqlite3 db.sqlite3 ".restore backup.db"
```
