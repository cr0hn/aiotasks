FROM python:3.5-slim

ENV GOSU_VERSION=1.9 \
    DEBUG=False \
    CFLAGS="-O3 -mtune=native"

# Update OS, add new user
RUN useradd -ms /bin/bash aiotasks_user

# Install Gosu to run with unprivileged user
ENV GOSU_VERSION 1.9
RUN set -x \
 && apt-get update && apt-get install -y --no-install-recommends ca-certificates wget \
 && apt-get install --no-install-recommends -y gcc python3-dev \
 && rm -rf /var/lib/apt/lists/* \
 && dpkgArch="$(dpkg --print-architecture | awk -F- '{ print $NF }')" \
 && wget -O /usr/local/bin/gosu "https://github.com/tianon/gosu/releases/download/$GOSU_VERSION/gosu-$dpkgArch" \
 && wget -O /usr/local/bin/gosu.asc "https://github.com/tianon/gosu/releases/download/$GOSU_VERSION/gosu-$dpkgArch.asc" \
 && export GNUPGHOME="$(mktemp -d)" \
 && gpg --keyserver ha.pool.sks-keyservers.net --recv-keys B42F6819007F00F88E364FD4036A9C25BF357DD4 \
 && gpg --batch --verify /usr/local/bin/gosu.asc /usr/local/bin/gosu \
 && rm -r "$GNUPGHOME" /usr/local/bin/gosu.asc \
 && chmod +x /usr/local/bin/gosu \
 && gosu nobody true \
 && apt-get purge -y --auto-remove ca-certificates wget

# Install dependencies
RUN apt-get install --no-install-recommends -y gcc python3-dev

# Install code
RUN pip install --upgrade pip
RUN pip install aiotasks[performance]

USER aiotasks_user
WORKDIR /home/aiotasks_user
ENTRYPOINT gosu /usr/local/bin/aiotasks