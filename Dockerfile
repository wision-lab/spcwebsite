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
    caddy

# And a few nice to haves for debugging and cleanup
RUN apt-get install -y sqlite3 ncdu tmux 
RUN curl https://getcroc.schollz.com | bash 
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

# Add the rest of the project source code
COPY . /app

# Collect the static files
RUN python manage.py collectstatic --noinput

# Copy configs
COPY .config/Caddyfile /etc/caddy/Caddyfile
COPY .config/supervisord.conf /etc/supervisord.conf

# Run with supervisord
CMD ["supervisord", "-c", "/etc/supervisord.conf"]
