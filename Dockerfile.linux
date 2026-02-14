FROM ubuntu:22.04

ARG DEBIAN_FRONTEND=noninteractive

# ── System build dependencies + Qt runtime libs needed by Slicer ──
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    subversion \
    ca-certificates \
    wget \
    curl \
    xz-utils \
    pkg-config \
    python3 \
    python3-pip \
    python3-setuptools \
    # GL / X11 / graphics
    libglu1-mesa-dev \
    libgl1-mesa-dev \
    libegl1-mesa-dev \
    libx11-dev \
    libx11-xcb-dev \
    libxcb1-dev \
    libxcb-glx0-dev \
    libxcb-keysyms1-dev \
    libxcb-image0-dev \
    libxcb-shm0-dev \
    libxcb-icccm4-dev \
    libxcb-sync-dev \
    libxcb-xfixes0-dev \
    libxcb-shape0-dev \
    libxcb-randr0-dev \
    libxcb-render-util0-dev \
    libxcb-xinerama0-dev \
    libxkbcommon-dev \
    libxkbcommon-x11-dev \
    libxt-dev \
    libxrender-dev \
    libxrandr-dev \
    # Audio / multimedia
    libpulse-dev \
    libasound2-dev \
    # SSL
    libssl-dev \
    # Font / dbus / misc
    libfontconfig1-dev \
    libfreetype-dev \
    libdbus-1-dev \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libpango-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# ── Install Qt 5.15.2 via aqtinstall (reliable, no Qt account needed) ──
RUN pip3 install aqtinstall \
    && aqt install-qt linux desktop 5.15.2 gcc_64 -m qtwebengine -O /opt/qt \
    && rm -rf /tmp/*

# Verify the install produced the expected cmake config
RUN ls /opt/qt/5.15.2/gcc_64/lib/cmake/Qt5/Qt5Config.cmake

WORKDIR /workspace

# Add entrypoint (the source tree is expected to be mounted at runtime)
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENV BUILD_TYPE=Release
ENV QT5_DIR=/opt/qt/5.15.2/gcc_64/lib/cmake/Qt5

ENTRYPOINT ["/docker-entrypoint.sh"]
