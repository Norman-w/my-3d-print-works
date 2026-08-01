FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive
ARG ESP_IDF_VERSION=v5.5.1

ENV TZ=Etc/UTC
ENV IDF_PATH=/opt/esp/idf
ENV IDF_TOOLS_PATH=/opt/espressif
ENV DISPLAY=:99
ENV PATH=/opt/esp/idf/tools:/opt/espressif/tools:$PATH

# SmartPaddle needs native CAD/EDA, CGO/SQLite, Web, Go and ESP32 toolchains.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bison \
        build-essential \
        ca-certificates \
        ccache \
        cmake \
        curl \
        dfu-util \
        flex \
        gawk \
        git \
        gperf \
        golang-go \
        libffi-dev \
        libgl1 \
        libssl-dev \
        libusb-1.0-0 \
        ninja-build \
        nodejs \
        npm \
        openscad \
        pkg-config \
        python3 \
        python3-pip \
        python3-venv \
        software-properties-common \
        unzip \
        wget \
        xz-utils \
        xvfb \
    && add-apt-repository --yes ppa:kicad/kicad-9.0-releases \
    && apt-get update \
    && apt-get install -y --no-install-recommends kicad kicad-libraries \
    && rm -rf /var/lib/apt/lists/*

# Firmware lockfile targets ESP-IDF 5.5.1 / ESP32-S3.
RUN mkdir -p /opt/esp /opt/espressif \
    && git clone --branch "${ESP_IDF_VERSION}" --depth 1 \
        --shallow-submodules --recurse-submodules \
        https://github.com/espressif/esp-idf.git /opt/esp/idf \
    && /opt/esp/idf/install.sh esp32s3 \
    && chmod -R a+rX /opt/esp /opt/espressif

WORKDIR /workspace
