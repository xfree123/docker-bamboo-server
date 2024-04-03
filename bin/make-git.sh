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
if command -v microdnf &> /dev/null; then
  echo "UBI image detected"
  microdnf update -y
  microdnf install -y --setopt=install_weak_deps=0 git git-lfs less make autoconf gcc zlib-devel libcurl-devel openssl-devel expat-devel
else
  apt-get update
  apt-get install -y --no-install-recommends git git-lfs less dh-autoreconf libcurl4-gnutls-dev libexpat1-dev libssl-dev make zlib1g-dev
fi

# cut -c53- here drops the SHA (40), tab (1) and "refs/tags/v" (11), because some things, like the
# snapshot URL and tarball root directory, don't have the leading "v" from the tag in them
# Thanks to Bryan Turner for this improved method of retrieving the appropriate git version
GIT_VERSION=$(git ls-remote git://git.kernel.org/pub/scm/git/git.git | cut -c53- | grep "^${SUPPORTED_GIT_VERSION}\.[0-9\.]\+$" | sort -V | tail -n 1)

# Define primary and backup URLs using the fetched Git version
PRIMARY_GIT_URL="https://git.kernel.org/pub/scm/git/git.git/snapshot/git-${GIT_VERSION}.tar.gz"
BACKUP_GIT_URL="https://github.com/git/git/archive/refs/tags/v${GIT_VERSION}.tar.gz"

download_git_src() {
    local git_url=$1
    local source_dir=$2

    echo "Attempting to download and extract Git from ${git_url}..."
    if curl -L -s -o - "${git_url}" | tar -xz --strip-components=1 --one-top-level="${source_dir}"; then
        echo "Downloaded and extracted successfully from ${git_url}."
        return 0
    else
        echo "Failed to download from ${git_url}."
        return 1
    fi
}

# Attempt to download and extract from the primary source
if ! download_git_src "${PRIMARY_GIT_URL}" "${SOURCE_DIR}"; then
    echo "Primary Git URL failed. Trying backup Git URL..."
    # Attempt to download and extract from the backup source
    if ! download_git_src "${BACKUP_GIT_URL}" "${SOURCE_DIR}"; then
        echo "Failed to download from backup Git URL."
        exit 1
    fi
fi

cd "${SOURCE_DIR}"

# Install git from source
make configure
./configure --prefix=/
make -j`nproc` NO_TCLTK=1 NO_GETTEXT=1 install

# Remove and clean up dependencies
echo "Removing dependencies and cleaning up"
cd /
rm -rf ${SOURCE_DIR}
if command -v microdnf &> /dev/null; then
  echo "UBI image detected. Removing dependencies"
  microdnf remove make gcc zlib-devel \
  libxcrypt-devel  \
  glibc-devel libcurl-devel openssl-devel expat-devel kernel-headers -y
  microdnf clean all
else
  apt-get purge -y dh-autoreconf
  apt-get clean autoclean
  apt-get autoremove -y
  rm -rf /var/lib/apt/lists/*
fi

echo "GIT VERSION **********************"
git --version
echo "GIT VERSION **********************"
