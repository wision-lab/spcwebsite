# Quick Setup

## Environment

### Dependencies

First clone the repo, and inside it, initialize and activate a venv using [uv](https://docs.astral.sh/uv/):
```
uv sync 
source .venv/bin/activate
```

### Environment variables

Evaluation variables:
- `SPC_UPLOADDIR`: Directory, where the uploaded submission files are stored.
- `SPC_EVALDIR`: Location of the non-public ground truth files needed for evaluation.
- `SPC_IMGDIR`: Directory in which qualitative evaluation frames from users are saved. 
- `SPC_DATABASEDIR`: Should point to a directory in a persistent volume, the evaluation envs should too. 
- `SPC_UPLOADS_ENABLED`: If false (or unset) users will not be able to upload anything.
- (optional) `TORCH_HOME`: You might want to set this to point to a mounted volume to increase cache hit rate.

Email & account creation variables:
- `SPC_EMAILUSER`: Email from which to send confirmation/password-reset/etc emails
- `SPC_EMAILPASSWORD`: App password for above email address, needs programmatic access.
- `SPC_EMAILHOST`: Host address for email, eg `smtp.gmail.com`.
- `SPC_FROMEMAIL`: Typically just equal to the same value as `SPC_EMAILUSER`.

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

Or batch upload a few submissions like so:
```
python manage.py multi_submit naivesums.json 
```

You can find sample naivesum submissions [here](https://drive.google.com/file/d/1YuBYVSToHNnZs0f2PBI_wJXmkhvNXsv_/view?usp=sharing).

## Running evaluation script

You can run the eval script periodically like so:
```
python manage.py evaluate_submissions
```

# Acknowledgements  

This website is loosely inspired off of the [Spring Benchmark website](https://spring-benchmark.org/) with the following notable modifications:
- Split user account logic and benchmark logic into separate apps (core vs eval)
- User.is_verified refers to user's email address, and is_active is true by default
- Logout action is now a POST request, as logout on GET was deprecated due to security concerns 
- Make submit view a class based view, perform server and client side validation, streamline logic
- Enable users to re-send verification email if logged in
- Add page for password change, SPRING uses [django's admin page](https://spring-benchmark.org/accounts/password_change/) for this
- Use enums for entry status and visibility, helps catch errors
- Make ResultEntry abstract to enable future evaluation types and easy entry editing via a form 
- Enable ascending and descending sort of entries on results page
- Enable users to delete their entries
- Enable user upload rate limit 
- Add progress bar to submission upload
- Use modelform for submission, allows for setting other fields directly
- Show user's private results on reconstruction page when logged in
- Allow for users to compare different submissions directly by selecting multiple rows in the results table 
- Ensure user uploaded submissions that are non-public are properly auth'd, use caddy's forward_auth for this
- Save user uploaded samples as a `ResultSample`, enables deleting of assets when user or submission is deleted
- Ensure evaluation cron job doesn't run if already running via flock, enables more frequent evals 
