FROM python:3.14.7-slim-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/
WORKDIR /code
ENV PATH="/code/.venv/bin:$PATH"
COPY pyproject.toml .python-version uv.lock ./
RUN uv --sync locked
COPY pipeline.py .

ENTRYPOINT ['python', 'pipeline.py']


# docker run -it --rm \
#   -e POSTGRES_USER="root" \
#   -e POSTGRES_PASSWORD="root" \
#   -e POSTGRES_DB="collector_vault" \
#   -v collector_vault_postgres_data:/var/lib/postgresql \
#   -p 5432:5432 \
#   postgres:18

# connect to docker postgres
#uv run pgcli -h localhost -p 5432 -u root -d collector_vault