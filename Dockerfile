FROM frolvlad/alpine-glibc:alpine-3.8
ARG VERSION
#ENV TZ="Europe/Zurich" - does not seem to work for Anaconda Python...
#See: https://remotemonitoringsystems.ca/time-zone-abbreviations.php
ENV TZ="CET-1CEST-2,M3.5.0/02:00:00,M10.5.0/03:00:00"
RUN CONDA_DIR="/opt/conda" && \
    CONDA_VERSION="4.9.2" && \
    CONDA_MD5_CHECKSUM="122c8c9beb51e124ab32a0fa6426c656" && \
    \
    apk add --no-cache --virtual=.build-dependencies wget bash && \
    apk add --no-cache ca-certificates tzdata && \
    \
    mkdir -p "$CONDA_DIR" && \
    wget "http://repo.continuum.io/miniconda/Miniconda3-py38_${CONDA_VERSION}-Linux-x86_64.sh" -O miniconda.sh && \
    echo "$CONDA_MD5_CHECKSUM  miniconda.sh" | md5sum -c && \
    bash miniconda.sh -f -b -p "$CONDA_DIR" && \
    rm miniconda.sh && \
    ln -s "$CONDA_DIR/etc/profile.d/conda.sh" /etc/profile.d/conda.sh && \
    \
    $CONDA_DIR/bin/conda update --yes conda && \
    $CONDA_DIR/bin/conda config --set auto_update_conda False && \
    $CONDA_DIR/bin/conda install --name=base --channel=anjos baker=$VERSION && \
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
ENV PATH="/opt/conda/bin:${PATH}"
ENTRYPOINT ["/opt/conda/bin/bake"]
CMD ["--help"]
