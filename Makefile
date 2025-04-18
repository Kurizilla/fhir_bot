# Makefile para automatizar FHIR Agent API

IMAGE=fhir-agent-api
REGISTRY=us-central1-docker.pkg.dev/g-stg-gsv000-tlmd-erp-prj-6fe2/fhir-agent-api-container/$(IMAGE)
PROJECT_ID=g-stg-gsv000-tlmd-erp-prj-6fe2
REGION=us-central1

build:
	@echo "🔨 Building Docker image..."
	docker build -t $(IMAGE) .

tag:
	@echo "🏷️ Tagging image..."
	docker tag $(IMAGE) $(REGISTRY):latest

push:
	@echo "📤 Pushing image to Artifact Registry..."
	docker push $(REGISTRY):latest

deploy:
	@echo "🚀 Deploying to Cloud Run..."
	gcloud run deploy $(IMAGE) \
		--image $(REGISTRY):latest \
		--region $(REGION) \
		--platform managed \
		--allow-unauthenticated \
		--project $(PROJECT_ID) \
		--set-env-vars GS_APIKEY=esJE70fUsGMGSqvz1k6WMAgf9Q2hH83xdsCUWl8IjCpFu4Tg

run:
	@echo "🚀 Running container locally..."
	docker run -d -p 8080:8080 \
		-e GS_APIKEY=esJE70fUsGMGSqvz1k6WMAgf9Q2hH83xdsCUWl8IjCpFu4Tg \
		--name fhir-agent-test \
		$(IMAGE)

stop:
	@echo "🛑 Stopping and removing local container..."
	docker stop fhir-agent-test || true
	docker rm fhir-agent-test || true

all: build tag push deploy
