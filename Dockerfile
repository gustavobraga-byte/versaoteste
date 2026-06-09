FROM python:3.11-slim

RUN apt-get update -qq && apt-get install -y -qq \
    git curl ttyd xclip xsel \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:${PATH}"

RUN curl -fsSL https://opencode.ai/install | bash || pip install opencode

WORKDIR /app
COPY . .

RUN pip install --quiet google-api-python-client google-auth-httplib2 google-auth-oauthlib

ENV TERM=xterm-256color
ENV OPENCODE_EXPERIMENTAL_DISABLE_COPY_ON_SELECT=1

EXPOSE 8000 8001

CMD ["python", "-c", "from main import run; run()"]
