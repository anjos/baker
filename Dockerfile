FROM condaforge/mambaforge:latest
ARG VERSION
#ENV TZ="Europe/Zurich" - does not seem to work for Anaconda Python...
#See: https://remotemonitoringsystems.ca/time-zone-abbreviations.php
ENV TZ="CET-1CEST-2,M3.5.0/02:00:00,M10.5.0/03:00:00"

# Install conda
RUN CONDA_DIR="/opt/conda" && \
    $CONDA_DIR/bin/conda config --set auto_update_conda False && \
    $CONDA_DIR/bin/mamba install --name=base --channel=anjos baker=$VERSION && \
    $CONDA_DIR/bin/conda clean --all --yes && \
    mkdir -p "$CONDA_DIR/locks" && \
    chmod 777 "$CONDA_DIR/locks" && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone && \
    echo $TZ > /etc/TZ

# Export this command
ENV PATH="/opt/mamba/bin:${PATH}"
ENTRYPOINT ["/opt/mamba/bin/bake"]
CMD ["--help"]
