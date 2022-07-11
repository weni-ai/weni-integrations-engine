FROM python:3.8-slim-buster AS base

ARG APP_UID=1000
ARG APP_GID=1000

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

ARG APP_PORT="8000"

ARG APP_VERSION="0.1"

# set environment variables
ENV PROJECT_PATH="/marketplace"

ENV APPLICATION_NAME="Marketplace"

ENV APP_VERSION=${APP_VERSION} \
  RUNTIME_DEPS=${RUNTIME_DEPS} \
  BUILD_DEPS=${BUILD_DEPS} \
  APP_UID=${APP_UID} \
  APP_GID=${APP_GID} \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONIOENCODING=UTF-8 \
  PIP_DISABLE_PIP_VERSION_CHECK=1 \
  PATH="/install/bin:${PATH}" \
  APP_PORT=${APP_PORT}

LABEL app=${VERSION} \
  os="debian" \
  os.version="10" \
  name="${APPLICATION_NAME} ${APP_VERSION}" \
  description="${APPLICATION_NAME} image" \
  maintainer="${APPLICATION_NAME} Team"

RUN addgroup --gid "${APP_GID}" app_group \
  && useradd --system -m -d ${PROJECT_PATH} -u "${APP_UID}" -g "${APP_GID}" app_user

# set work directory
WORKDIR ${PROJECT_PATH}

FROM base AS build

RUN if [ ! "x${BUILD_DEPS}" = "x" ] ; then apt-get update \
  && apt-get install -y --no-install-recommends ${BUILD_DEPS} ; fi

FROM build as build-poetry

COPY ./pyproject.toml .
COPY ./poetry.lock .

RUN python -m pip install -U poetry \
  && poetry export --output /requirements.txt

FROM build as build-pip

COPY --from=build-poetry /requirements.txt .

RUN mkdir /install \
  && pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM base

COPY --from=build-pip /install /usr/local

# Clear image and install runtime dependences
RUN apt-get update \
  && SUDO_FORCE_REMOVE=yes apt-get remove --purge -y ${BUILD_DEPS} \
  && apt-get autoremove -y \
  && apt-get install -y --no-install-recommends ${RUNTIME_DEPS} \
  && rm -rf /usr/share/man \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# copy project
COPY --chown=app_user:app_group . .

ENTRYPOINT ["/marketplace/docker-entrypoint.sh"]
