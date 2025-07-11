# Makefile para automatizar FHIR Agent API

IMAGE=fhir-agent-api
REGISTRY=us-central1-docker.pkg.dev/g-stg-gsv000-tlmd-erp-prj-6fe2/fhir-agent-api-container/$(IMAGE)
PROJECT_ID=g-stg-gsv000-tlmd-erp-prj-6fe2
REGION=us-central1

build:
	@echo "🔨 Building Docker image..."
	docker build --platform linux/amd64 -t $(IMAGE) .

tag:
	@echo "🏷️ Tagging image..."
	docker tag $(IMAGE) $(REGISTRY):latest

push:
	@echo "📤 Pushing image to Artifact Registry..."
	docker push $(REGISTRY):latest

deploy: build tag push
	@echo "🚀 Deploying to Cloud Run..."
	gcloud run deploy $(IMAGE) \
		--image $(REGISTRY):latest \
		--region $(REGION) \
		--platform managed \
		--allow-unauthenticated \
		--project $(PROJECT_ID) \
		--set-env-vars GS_APIKEY=$(GS_APIKEY) \
		--set-env-vars MEDLM_PROJECT=$(MEDLM_PROJECT)

run: build
	@echo "🚀 Running container locally..."
	docker run -p 8080:8080 \
  		-e GS_APIKEY=$(GS_APIKEY) \
  		-e MEDLM_PROJECT=$(MEDLM_PROJECT) \
  		fhir-agent-api

stop:
	@echo "🛑 Stopping and removing local container..."
	docker stop fhir-agent-test-dev || true
	docker rm fhir-agent-test-dev || true

all: build tag push deploy
