FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /bin/uv
WORKDIR /app
ENV FASTEMBED_CACHE_PATH=/app/.models PATH="/app/.venv/bin:$PATH"
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project
# bake the embedding model (about 220 MB) into the image so questions work offline
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')"
COPY rag_lgpd ./rag_lgpd
COPY data ./data
RUN uv sync --frozen --no-dev
ENTRYPOINT ["rag-lgpd"]
CMD ["avaliar-busca"]
