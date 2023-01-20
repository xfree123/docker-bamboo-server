#!/bin/bash

set -e

SOURCE_DIR="/git_source"

: ${BAMBOO_VERSION=}
BAMBOO_MAJOR_VERSION=$(echo "${BAMBOO_VERSION}" | cut -d. -f-1)
BAMBOO_MINOR_VERSION=$(echo "${BAMBOO_VERSION}" | cut -d. -f-2)


# Bamboo uses git as a client and has pretty broad version support, so
# we don't need to pin a max supported version for every release. It's
# still nice to be able to control git versions in future if the need
# arises, so it seems worth leaving this here for now
case ${BAMBOO_MAJOR_VERSION} in
    7)  SUPPORTED_GIT_VERSION="2.39" ;;
    8)  SUPPORTED_GIT_VERSION="2.39" ;;
    9)  SUPPORTED_GIT_VERSION="2.39" ;;
    *)  SUPPORTED_GIT_VERSION="2.39" ;;
esac


# Install build dependencies
echo "Installing git build dependencies"
apt-get update
apt-get install -y --no-install-recommends git git-lfs less dh-autoreconf libcurl4-gnutls-dev libexpat1-dev libssl-dev make zlib1g-dev

# cut -c53- here drops the SHA (40), tab (1) and "refs/tags/v" (11), because some things, like the
# snapshot URL and tarball root directory, don't have the leading "v" from the tag in them
# Thanks to Bryan Turner for this improved method of retrieving the appropriate git version
GIT_VERSION=$(git ls-remote git://git.kernel.org/pub/scm/git/git.git | cut -c53- | grep "^${SUPPORTED_GIT_VERSION}\.[0-9\.]\+$" | sort -V | tail -n 1)
curl -s -o - "https://git.kernel.org/pub/scm/git/git.git/snapshot/git-${GIT_VERSION}.tar.gz" | tar -xz --strip-components=1 --one-top-level="${SOURCE_DIR}"
cd "${SOURCE_DIR}"

# Install git from source
make configure
./configure --prefix=/
make -j`nproc` NO_TCLTK=1 NO_GETTEXT=1 install

# Remove and clean up dependencies
cd /
rm -rf ${SOURCE_DIR}
apt-get purge -y dh-autoreconf
apt-get clean autoclean
apt-get autoremove -y
rm -rf /var/lib/apt/lists/*
