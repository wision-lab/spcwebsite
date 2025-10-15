# Deployment Notes 

*Note:* This is not meant to be a guide on how to deploy a django app, it just serves as a reference for project maintainers.  

First and foremost, see the [django deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/).

All environment variables must be set, with `SPC_DEBUG=False` (or equivalently unset), and since most hosts will block SMTP traffic, we use a email service to send verification emails. The code uses [resend](https://resend.com/) to do this, so we'll need to set the `RESEND_API_KEY` envvar as well. We fall back to django's smtp functionality if the api key is not found (only for use in development). This means the following envvars are unused when in prod: `SPC_EMAILUSER`, `SPC_EMAILPASSWORD`, `SPC_EMAILHOST`. 


# Docker Setup

Create a `docker.env` file with the required envvars:
```
SPC_DEBUG=False
SPC_DATABASEDIR=/storage
SPC_UPLOADDIR=/storage/uploads
SPC_EVALDIR=/storage/datasets
SPC_IMGDIR=/storage/media
SPC_EMAILUSER=...
RESEND_API_KEY=...
SPC_SECRET_KEY=...
```

*Note:* The paths here are location inside the container. You'll need to map these to your local folders by mounting volumes.  


Then you can build the docker image while passing all environment variables from this file:
```
docker build -t website-img $(cat docker.env | sed 's@^@--build-arg @g' | paste -s -d " ") . 
```

Once built, it may we useful to run the container in interactive mode to poke around, or `makemigrations`:
```
docker run --env-file docker.env -v ../storage/:/storage/ -it website-img bash
```

You can spin up the server like so:
```
docker run -p 8000:80 -v ../storage:/storage/ --env-file docker.env website-img 
```


# Dataset backup and restore

In `$SPC_DATABASEDIR`, you can simply:
```
sqlite3 db.sqlite3 ".backup backup.db"
sqlite3 db.sqlite3 ".restore backup.db"
```
