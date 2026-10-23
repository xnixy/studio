FROM python:3.12-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PATH="/usr/local/share/npm-global/bin:${PATH}" \
    NPM_CONFIG_PREFIX=/usr/local/share/npm-global

# System tools + ffmpeg (video render pipeline) + Node 22 for the Vite frontend
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        ffmpeg \
        git \
        gnupg \
        openssh-client \
        procps \
        sudo \
        unzip \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && mkdir -p /usr/local/share/npm-global \
    && npm install -g npm@latest \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspaces/studio

# Keep the container alive; Zed / the devcontainer CLI attach to this service.
CMD ["sleep", "infinity"]
