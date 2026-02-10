# syntax=docker/dockerfile:1.7

# ==============================================================================
# Base Stage
#
# Installs Python, common dependencies, creates a non-root user, and sets up
# the basic environment. Used as a foundation for both development and
# production stages.
# ==============================================================================
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  PIP_NO_CACHE_DIR=1 \
  PYTHONPATH=/usr/src/app/src

WORKDIR /usr/src/app

# Install minimal system dependencies required by both dev and prod
RUN apt-get update && apt-get install -y --no-install-recommends \
  libpq-dev \
  postgresql-client \
  netcat-openbsd \
  dos2unix \
  && rm -rf /var/lib/apt/lists/*

# Create a non-root user for security
ARG USERNAME=appuser
ARG USER_UID=1000
ARG USER_GID=$USER_UID
RUN groupadd --gid $USER_GID $USERNAME \
  && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
  && mkdir -p /usr/src/app/logs /usr/src/app/static /usr/src/app/media \
  && chown -R $USERNAME:$USERNAME /usr/src/app

# Copy entrypoint scripts and fix line endings
COPY --chmod=755 scripts/ /opt/docker/scripts/
RUN find /opt/docker/scripts -type f -name "*.sh" -exec dos2unix {} \;

# ==============================================================================
# Production Stage
#
# Builds a lean, optimized image for production. It installs only production
# Python packages and copies the application code.
# ==============================================================================
FROM base AS production

# Install production dependencies
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel \
  && pip install -r requirements.txt

# Switch to the non-root user
USER $USERNAME

# Copy application code
COPY --chown=$USERNAME:$USERNAME . .

EXPOSE 8000

# The entrypoint script will start the gunicorn server in production
ENTRYPOINT ["/bin/bash", "/opt/docker/scripts/entrypoint.sh"]


# ==============================================================================
# Development Stage
#
# Builds a feature-rich image for local development. Includes all dev tools,
# installs dev packages, and sets up Oh My Zsh.
# ==============================================================================
FROM base AS development

# Install additional system dependencies for development
RUN apt-get update && apt-get install -y --no-install-recommends \
  build-essential \
  gcc \
  curl \
  ca-certificates \
  git \
  zsh \
  nano \
  openssh-client \
  gpg \
  sudo \
  && echo "appuser ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/appuser \
  && rm -rf /var/lib/apt/lists/*

# Install GitHub CLI (gh)
RUN mkdir -p -m 755 /etc/apt/keyrings && \
  curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null && \
  chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg && \
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list > /dev/null && \
  apt-get update && \
  apt-get install gh -y

# Install both production and development Python packages
COPY requirements.txt .
COPY requirements-dev.txt .
RUN pip install --upgrade pip setuptools wheel \
  && pip install -r requirements.txt \
  && pip install -r requirements-dev.txt \
  && pip install debugpy

# Change user's default shell to zsh
RUN chsh -s /bin/zsh $USERNAME

# Switch to the non-root user
USER $USERNAME

# Set path for user-installed packages
ENV PATH="/usr/local/bin:/home/appuser/.local/bin:$PATH"

# Install Oh My Zsh and plugins
RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended
RUN git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions
RUN git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting
RUN echo 'export ZSH="$HOME/.oh-my-zsh"' > ~/.zshrc && \
  echo 'ZSH_THEME="robbyrussell"' >> ~/.zshrc && \
  echo 'plugins=(git python docker docker-compose pip virtualenv colored-man-pages command-not-found zsh-autosuggestions zsh-syntax-highlighting)' >> ~/.zshrc && \
  echo 'source $ZSH/oh-my-zsh.sh' >> ~/.zshrc

# Copy application code
COPY --chown=$USERNAME:$USERNAME . .

EXPOSE 8000 5678

# The entrypoint script will start the Django development server
ENTRYPOINT ["/bin/bash", "/opt/docker/scripts/entrypoint.sh"]
