# syntax = docker/dockerfile:1

ARG PYTHON_VERSION="3.9"
ARG DEBIAN_VERSION="bookworm"
ARG POETRY_VERSION="1.7.0"

ARG BUILD_DEPS="\
  python3-dev \
  build-essential \
  gettext \
  libpq-dev \
  cmake \
  pkg-config \
  autoconf \
  libtool \
  automake"

ARG RUNTIME_DEPS="\
  tzdata \
  curl \
  gosu \
  gettext \
  postgresql-client"


FROM python:${PYTHON_VERSION}-slim-${DEBIAN_VERSION} as base

ARG POETRY_VERSION
ARG BUILD_DEPS
ARG RUNTIME_DEPS

ENV PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  DEBIAN_FRONTEND=noninteractive \
  PROJECT=Marketplace \
  PROJECT_PATH=/marketplace \
  PROJECT_USER=app_user \
  PROJECT_GROUP=app_group \
  PIP_DISABLE_PIP_VERSION_CHECK=1 \
  PATH="/install/bin:${PATH}" \
  APP_PORT=8000 \
  APPLICATION_NAME="Marketplace" \
  RUNTIME_DEPS=${RUNTIME_DEPS} \
  BUILD_DEPS=${BUILD_DEPS} \
  PYTHONIOENCODING=UTF-8

ARG COMPRESS_ENABLED
ARG BRANDING_ENABLED
 
ARG RAPIDPRO_APPS_GIT_URL
ARG RAPIDPRO_APPS_GIT_BRANCH

LABEL app=${VERSION} \
  os="debian" \
  os.version="10" \
  name="Weni-integrations-engine" \
  description="Weni-integrations-engine image" \
  maintainer="https://github.com/weni-ai" \
  org.opencontainers.image.url="https://github.com/weni-ai/weni-integrations-engine" \
  org.opencontainers.image.documentation="https://github.com/weni-ai/weni-integrations-engine" \
  org.opencontainers.image.source="https://github.com/weni-ai/weni-integrations-engine" \
  org.opencontainers.image.title="Weni-integrations-engine"

RUN addgroup --gid 1999 "${PROJECT_GROUP}" \
  && useradd --system -m -d "${PROJECT_PATH}" -u 1999 -g 1999 "${PROJECT_USER}"

WORKDIR "${PROJECT_PATH}"

RUN rm -f /etc/apt/apt.conf.d/docker-clean; echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache

FROM base as build-poetry

ARG POETRY_VERSION
ARG REQUESTS_VERSION

COPY pyproject.toml poetry.lock ./

RUN --mount=type=cache,mode=0755,target=/pip_cache,id=pip pip install --cache-dir /pip_cache -U poetry=="${POETRY_VERSION}" \
  && poetry cache clear -n --all pypi \
  && poetry export --without-hashes --output requirements.txt
#  && poetry add -n --lock $(cat pip-requires.txt) \

FROM base as build

ARG BUILD_DEPS

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
  --mount=type=cache,target=/var/lib/apt,sharing=locked \
  apt-get update \
  && apt-get install --no-install-recommends --no-install-suggests -y ${BUILD_DEPS}
 
COPY --from=build-poetry "${PROJECT_PATH}/requirements.txt" /tmp/dep/
RUN --mount=type=cache,mode=0755,target=/pip_cache,id=pip pip install --cache-dir /pip_cache --prefix=/install -r /tmp/dep/requirements.txt

FROM base

ARG BUILD_DEPS
ARG RUNTIME_DEPS

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
  --mount=type=cache,target=/var/lib/apt,sharing=locked \
  apt-get update \
  && SUDO_FORCE_REMOVE=yes apt-get remove --purge -y ${BUILD_DEPS} \
  && apt-get autoremove -y \
  && apt-get install -y --no-install-recommends ${RUNTIME_DEPS} \
  && rm -rf /usr/share/man /usr/share/doc

COPY --from=build /install /usr/local
COPY --chown=${PROJECT_USER}:${PROJECT_GROUP} . ${PROJECT_PATH}

USER "${PROJECT_USER}:${PROJECT_USER}"
EXPOSE 8000
ENTRYPOINT ["bash", "./docker/start"]
CMD ["start"]
