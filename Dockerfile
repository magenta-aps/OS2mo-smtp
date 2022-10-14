FROM python:3.10

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1
RUN pip install --no-cache-dir poetry==1.1.13

WORKDIR /opt
COPY poetry.lock pyproject.toml ./
RUN poetry install --no-dev

WORKDIR /opt/app
COPY mo_smtp .
WORKDIR /opt/

CMD ["poetry", "run", "python", "-m",  "mo_smtp.ldap_agent"]

# Add build version to the environment last to avoid build cache misses
ARG COMMIT_TAG
ARG COMMIT_SHA
ENV COMMIT_TAG=${COMMIT_TAG:-HEAD} \
    COMMIT_SHA=${COMMIT_SHA}
