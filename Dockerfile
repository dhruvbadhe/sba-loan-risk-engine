
FROM python:3.10-slim as builder

WORKDIR /code


RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ libgomp1 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --user -r requirements.txt


FROM python:3.10-slim

WORKDIR /code


RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*


COPY --from=builder /root/.local /root/.local
COPY ./app /code/app


ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

EXPOSE 8000


CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]