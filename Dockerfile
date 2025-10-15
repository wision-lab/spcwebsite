# Use a slim Debian image as our base
FROM debian:bookworm-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies needed by our app
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \ 
    wget \
    supervisor \
    caddy \ 
    cron

# And a few nice to haves for debugging and cleanup
RUN apt-get install -y sqlite3 ncdu tmux htop nano
RUN curl https://getcroc.schollz.com | bash 
RUN curl https://getmic.ro | bash
RUN mv micro /usr/local/bin/
RUN rm -rf /var/lib/apt/lists/*

# Install uv, the fast Python package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV PATH="/root/.local/bin:${PATH}"

# Install the project's dependencies using the lockfile and settings
COPY uv.lock pyproject.toml .python-version ./
RUN uv sync --locked --no-install-project --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Envvars needed during build
ARG SPC_DEBUG 
ARG SPC_UPLOADDIR
ARG SPC_EVALDIR
ARG SPC_IMGDIR
ARG SPC_DATABASEDIR
ARG RESEND_API_KEY
ARG SPC_SECRET_KEY
ARG SPC_NUM_THREADS
ARG TORCH_HOME

# Save them to an env file so the cronjob can source them
RUN echo SPC_DEBUG=${SPC_DEBUG} >> /etc/environment 
RUN echo SPC_UPLOADDIR=${SPC_UPLOADDIR} >> /etc/environment 
RUN echo SPC_EVALDIR=${SPC_EVALDIR} >> /etc/environment 
RUN echo SPC_IMGDIR=${SPC_IMGDIR} >> /etc/environment 
RUN echo SPC_DATABASEDIR=${SPC_DATABASEDIR} >> /etc/environment 
RUN echo RESEND_API_KEY=${RESEND_API_KEY} >> /etc/environment 
RUN echo SPC_SECRET_KEY=${SPC_SECRET_KEY} >> /etc/environment 
RUN echo SPC_NUM_THREADS=${SPC_NUM_THREADS} >> /etc/environment 
RUN echo TORCH_HOME=${TORCH_HOME} >> /etc/environment 

# Add the rest of the project source code
COPY . /app

# Collect the static files
RUN python manage.py collectstatic --noinput

# Copy configs
COPY .config/Caddyfile /etc/caddy/Caddyfile
COPY .config/supervisord.conf /etc/supervisord.conf

# Configure cron jobs, and ensure crontab-file permissions
COPY cron.d /etc/cron.d/
RUN chmod 0644 /etc/cron.d/*
RUN chown root:root /etc/cron.d/*

# Run with supervisord
CMD ["supervisord", "-c", "/etc/supervisord.conf"]
