**Note**: This Docker image has been published as both `atlassian/bamboo` and `atlassian/bamboo-server` up until February 15, 2024.
Both names refer to the same image. However, post-February 15, 2024, the `atlassian/bamboo-server` version ceased receiving updates, including both existing and new tags.
If you have been using `atlassian/bamboo-server`, switch to the `atlassian/bamboo` image to ensure access to the latest updates and new tags.

---

![Atlassian Bamboo](https://wac-cdn.atlassian.com/dam/jcr:560a991e-c0e3-4014-bd7d-2e65d4e4c84a/bamboo-icon-gradient-blue.svg?cdnVersion=814)

Bamboo is a continuous integration and deployment tool that ties automated builds, tests and releases together in a single workflow.

Learn more about Bamboo: [https://www.atlassian.com/software/bamboo](https://www.atlassian.com/software/bamboo)

# Overview

This Docker container makes it easy to get an instance of Bamboo up and running.

**Use docker version >= 20.10.10**

# Build stage

docker build --tag bamboo-server:9.6.5 --build-arg BAMBOO_VERSION=9.6.5 .
 
# Quick Start

For the `BAMBOO_HOME` directory that is used to store the repository data
(amongst other things) we recommend mounting a host directory as a [data
volume](https://docs.docker.com/engine/tutorials/dockervolumes/#/data-volumes),
or via a named volume.

Additionally, if running Bamboo in Data Center mode it is required that a
shared filesystem is mounted.

To get started you can use a data volume, or named volumes. In this example
we'll use named volumes.

    $> docker volume create --name bambooVolume
    $> docker run -v bambooVolume:/var/atlassian/application-data/bamboo --name="bamboo" -d -p 8085:8085 -p 54663:54663 atlassian/bamboo


**Success**. Bamboo is now available on [http://localhost:8085](http://localhost:8085)*

Please ensure your container has the necessary resources allocated to it. We
recommend 2GiB of memory allocated to accommodate the application server. See
[System
Requirements](https://confluence.atlassian.com/display/BAMBOO/Bamboo+Best+Practice+-+System+Requirements)
for further information.

_* Note: If you are using `docker-machine` on Mac OS X, please use `open http://$(docker-machine ip default):8085` instead._

# Advanced Usage
For advanced usage, e.g. configuration, troubleshooting, supportability, etc.,
please check the [**Full Documentation**](https://atlassian.github.io/data-center-helm-charts/containers/BAMBOO/).

