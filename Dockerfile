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
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=.python-version,target=.python-version \
    uv sync --locked --no-install-project --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Add the rest of the project source code
COPY . /app

# Migrate the database
RUN python manage.py makemigrations core eval
RUN python manage.py migrate

# Collect the static files
RUN python manage.py collectstatic --noinput

EXPOSE 80

# Copy configs
COPY .config/Caddyfile /etc/caddy/Caddyfile
COPY .config/supervisord.conf /etc/supervisord.conf

# Run with supervisord
CMD ["supervisord", "-c", "/etc/supervisord.conf"]
