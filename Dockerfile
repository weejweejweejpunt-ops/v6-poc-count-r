# This specifies our base image. This base image contains some commonly used
# dependancies and an install from all vantage6 packages.
ARG BASE=5.0
FROM ghcr.io/vantage6/infrastructure/algorithm-base:${BASE}

# Links the image on ghcr.io to this repository. Without it a GitHub Actions workflow can create the package,
# but a later release may be refused write access to it.
LABEL org.opencontainers.image.source="https://github.com/weejweejweejpunt-ops/v6-poc-count-r"
LABEL org.opencontainers.image.description="vantage6 v5 proof of concept: federated count of rows per value of a column, counted in R"

# R for the counting (the Debian packages; jsonlite is the only R package that is needed). The check makes the build
# fail here, and not at the first task, if R or jsonlite is not usable.
RUN apt-get update \
    && apt-get install -y --no-install-recommends r-base-core r-cran-jsonlite \
    && rm -rf /var/lib/apt/lists/* \
    && Rscript --vanilla -e 'library(jsonlite); cat(R.version.string, "with jsonlite", as.character(packageVersion("jsonlite")), "\n")'

# A UTF-8 locale, so that R reads and writes text in the same encoding as Python.
ENV LC_ALL=C.UTF-8

# Change this to the package name of your project.
ARG PKG_NAME="v6_poc_count_r"

# This will install your algorithm into this image (including the R files in the package).
COPY . /app
RUN uv pip install --system -e /app

# This will run your algorithm when the Docker container is started. The
# wrapper takes care of the IO handling (communication between node and
# algorithm). You dont need to change anything here.
ENV PKG_NAME=${PKG_NAME}
CMD python -c "from vantage6.algorithm.tools.wrap import wrap_algorithm; wrap_algorithm()"
