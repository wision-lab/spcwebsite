# Quick Setup

## Create environment
```
micromamba create -n website python==3.12
micromamba activate website
pip install -r requirements
```

## Environment variables

Evaluation variables:
- `SPC_UPLOADDIR`: directory, where the uploaded submission files are stored.
- `SPC_EVALDIR`: location of the non-public ground truth files needed for evaluation.
- `SPC_IMGDIR`: directory in which qualitative evaluation frames from users are saved. 
- `SPC_DATABASEDIR`: Should point to a directory in a persistent volume, the evaluation envs should too. 
- `SPC_UPLOADS_ENABLED`: If false (or unset) users will not be able to upload anything.

Email & account creation variables:
- `SPC_EMAILUSER`: email from which to send confirmation/password-reset/etc emails
- `SPC_EMAILPASSWORD`: app password for above email address, needs programmatic access.
- `SPC_EMAILHOST`: host address for email, eg `smtp.gmail.com`.
- `SPC_FROMEMAIL`: typically just equal to the same value as `SPC_EMAILUSER`.

See [email settings](https://docs.djangoproject.com/en/5.2/topics/email/) for more. 

Deployment Variables:
- `SPC_DEBUG`: Whether to run the server in debug mode, must be false when deployed. 
- `SPC_SECRET_KEY`: Django secret key, must be set when deployed. You can generate a new one using `secrets.token_urlsafe`.
- `SPC_NUM_THREADS`: Limit pytorch to this number of threads. Defaults to 1. Only used by eval script.

## Initialize database

First we need to `makemigrations` to create the SQL commands which will instantiate the right tables for the user accounts (in the `core` app) and submissions (in the `eval` app), then we can then execute this transaction with `migrate`:
```
python manage.py makemigrations core eval
python manage.py migrate
```

Now you should be able to create a superuser account like so:
```
python manage.py createsuperuser
```

## Start Server

Start website server: 
```
python manage.py runserver
```

Optionally create `<num>` entries with random numbers:
```
python manage.py create_random <num> --users=3
```

## Running evaluation script

You can run the eval script periodically like so:
```
python manage.py evaluate_submissions
```
