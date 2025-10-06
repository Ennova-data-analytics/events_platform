FROM python:3.11-slim as builder

WORKDIR /app

RUN pip install poetry

RUN poetry config virtualenvs.create false

COPY poetry.lock pyproject.toml /app/

RUN poetry install --no-interaction --no-ansi --no-root --only main

FROM python:3.11-slim

WORKDIR /app


COPY --from=builder /usr/local /usr/local

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

