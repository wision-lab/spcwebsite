# Use a slim Debian image as our base
FROM debian:bookworm-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies needed by our app
RUN apt-get update && apt-get install -y \
    build-essential \
    curl wget \
    supervisor \
    caddy \
    && rm -rf /var/lib/apt/lists/*

# Install uv, the fast Python package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV PATH="/root/.local/bin:${PATH}"

# Install the project's dependencies using the lockfile and settings
COPY uv.lock pyproject.toml .python-version ./
RUN uv sync --locked --no-install-project --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Add the rest of the project source code
COPY . /app

# Envvars needed during build
ARG SPC_DEBUG 
ARG SPC_UPLOADDIR
ARG SPC_EVALDIR
ARG SPC_IMGDIR
ARG RESEND_API_KEY
ARG SPC_SECRET_KEY

# Migrate the database
RUN python manage.py makemigrations core eval
RUN python manage.py migrate

# Collect the static files
RUN python manage.py collectstatic --noinput

# Copy configs
COPY .config/Caddyfile /etc/caddy/Caddyfile
COPY .config/supervisord.conf /etc/supervisord.conf

# Run with supervisord
CMD ["supervisord", "-c", "/etc/supervisord.conf"]
