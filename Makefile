VANTAGE6_VERSION ?= 5.0.3
TAG ?= latest
REGISTRY ?= ghcr.io/weejweejweejpunt-ops
PLATFORMS ?= linux/amd64
IMAGE ?= ${REGISTRY}/v6-poc-count-r

VANTAGE6_MAJOR := $(firstword $(subst ., ,$(VANTAGE6_VERSION)))

INCLUDE_V6_MAJOR_TAG ?= true

PUSH_REG ?= false

# We use a conditional (true on any non-empty string) later. To avoid
# accidents, we don't use user-controlled PUSH_REG directly.
# See: https://www.gnu.org/software/make/manual/html_node/Conditional-Functions.html
# The algorithm store resolves the image digest with an Accept header for the plain Docker v2 manifest only. A recent
# buildx pushes an OCI image index with attestations by default, which the store cannot read (HTTP 404). So: no
# provenance/SBOM attestations, and Docker media types. This needs the docker-container builder (created below).
BUILDER ?= v6-builder

_output :=
ifeq ($(PUSH_REG), true)
	_output := --output type=image,push=true,oci-mediatypes=false
endif

image:
	@set -e; \
	echo "Building ${IMAGE}:${TAG}-v6-${VANTAGE6_VERSION}"; \
	echo "Building ${IMAGE}:latest"; \
	EXTRA_MAJOR=""; \
	if [ "$(INCLUDE_V6_MAJOR_TAG)" = true ]; then \
	  echo "Building ${IMAGE}:${VANTAGE6_MAJOR}"; \
	  EXTRA_MAJOR='--tag ${IMAGE}:${VANTAGE6_MAJOR}'; \
	fi; \
	docker buildx inspect ${BUILDER} > /dev/null 2>&1 || docker buildx create --name ${BUILDER} --driver docker-container > /dev/null; \
	docker buildx build \
		--builder ${BUILDER} \
		--provenance=false \
		--sbom=false \
		--tag ${IMAGE}:${TAG}-v6-${VANTAGE6_VERSION} \
		--tag ${IMAGE}:latest \
		$$EXTRA_MAJOR \
		--platform ${PLATFORMS} \
		-f ./Dockerfile \
		${_output} .
