.PHONY: help run-local docker-build docker-up docker-down k8s-deploy k8s-delete demo-self-heal demo-hpa demo-failover cost-report test pdf

help:
	@echo "====================================================================="
	@echo "Twitter TrendPulse - Cloud Computing Project Commands"
	@echo "====================================================================="
	@echo "  make run-local      : Run FastAPI web server locally with python"
	@echo "  make docker-build   : Build optimized and baseline Docker images"
	@echo "  make docker-up      : Start Web App + Redis via Docker Compose"
	@echo "  make docker-down    : Stop Docker Compose services"
	@echo "  make k8s-deploy     : Deploy Redis, Web App (2 replicas) on Kubernetes"
	@echo "  make k8s-delete     : Tear down Kubernetes deployments & services"
	@echo "  make demo-self-heal : Execute Task 2 Pod Self-Healing Demonstration"
	@echo "  make demo-hpa       : Execute Task 3 HPA Autoscaling & Load Test"
	@echo "  make demo-failover  : Execute Task 4 Hybrid Cloud Failover Demonstration"
	@echo "  make cost-report    : Execute Task 5 Cost Optimization Measurement Analysis"
	@echo "  make pdf            : Convert Research Paper to PDF document"
	@echo "  make test           : Run unit test suite"
	@echo "====================================================================="

test:
	python3 -m unittest discover -s tests -p "test_*.py"

run-local:
	python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

docker-build:
	docker build -t trendpulse-app:optimized -f Dockerfile .
	docker build -t trendpulse-app:unoptimized -f Dockerfile.unoptimized .

docker-up:
	docker compose up -d

docker-down:
	docker compose down -v

k8s-deploy:
	kubectl apply -f k8s/namespace.yaml
	kubectl apply -f k8s/redis-deployment.yaml
	kubectl apply -f k8s/redis-service.yaml
	kubectl apply -f k8s/app-deployment.yaml
	kubectl apply -f k8s/app-service.yaml
	kubectl apply -f k8s/hpa.yaml

k8s-delete:
	kubectl delete -f k8s/hpa.yaml --ignore-not-found
	kubectl delete -f k8s/app-service.yaml --ignore-not-found
	kubectl delete -f k8s/app-deployment.yaml --ignore-not-found
	kubectl delete -f k8s/redis-service.yaml --ignore-not-found
	kubectl delete -f k8s/redis-deployment.yaml --ignore-not-found
	kubectl delete -f k8s/namespace.yaml --ignore-not-found

demo-self-heal:
	bash scripts/demo_self_healing.sh

demo-hpa:
	bash scripts/demo_hpa_scaling.sh

demo-failover:
	bash scripts/demo_failover.sh

cost-report:
	python3 scripts/cost_analysis.py

pdf:
	python3 scripts/convert_to_pdf.py

