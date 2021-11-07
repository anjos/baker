FROM frolvlad/alpine-glibc:alpine-3.9
ARG VERSION
#ENV TZ="Europe/Zurich" - does not seem to work for Anaconda Python...
#See: https://remotemonitoringsystems.ca/time-zone-abbreviations.php
ENV TZ="CET-1CEST-2,M3.5.0/02:00:00,M10.5.0/03:00:00"
RUN CONDA_DIR="/opt/mamba" && \
    CONDA_VERSION="4.10.3-6" && \
    CONDA_MD5_CHECKSUM="4f15aed175ef51f86ec7d2e7a59953cf" && \
    \
    apk add --no-cache --virtual=.build-dependencies wget bash && \
    apk add --no-cache ca-certificates tzdata && \
    \
    mkdir -p "$CONDA_DIR" && \
    wget "https://github.com/conda-forge/miniforge/releases/download/4.10.3-6/Mambaforge-${CONDA_VERSION}-Linux-x86_64.sh" -O miniconda.sh && \
    echo "$CONDA_MD5_CHECKSUM  miniconda.sh" | md5sum -c && \
    bash miniconda.sh -f -b -p "$CONDA_DIR" && \
    rm miniconda.sh && \
    ln -s "$CONDA_DIR/etc/profile.d/conda.sh" /etc/profile.d/conda.sh && \
    \
    $CONDA_DIR/bin/mamba update --yes conda && \
    $CONDA_DIR/bin/mamba config --set auto_update_conda False && \
    $CONDA_DIR/bin/mamba install --name=base --channel=anjos --channel=conda-forge baker=$VERSION && \
    rm -r "$CONDA_DIR/pkgs/" && \
    \
    apk del --purge .build-dependencies && \
    rm -f .build-dependencies && \
    \
    mkdir -p "$CONDA_DIR/locks" && \
    chmod 777 "$CONDA_DIR/locks" && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone && \
    echo $TZ > /etc/TZ
ENV PATH="/opt/mamba/bin:${PATH}"
ENTRYPOINT ["/opt/mamba/bin/bake"]
CMD ["--help"]
