.PHONY: test compile docker-build docker-run-train docker-build-serve docker-run-serve k8s-train k8s-serve k8s-status

test:
	python -m pytest -q

compile:
	python -m compileall -q src tests

docker-build:
	docker build -f docker/Dockerfile.train -t mlops-train:v1 .

docker-run-train:
	mkdir -p data checkpoints
	docker run --rm --shm-size=2g \
	  -v "$(PWD)/data:/app/data" \
	  -v "$(PWD)/checkpoints:/app/checkpoints" \
	  mlops-train:v1

docker-build-serve:
	docker build -f docker/Dockerfile.serve -t mlops-serve:v1 .

docker-run-serve:
	docker run --rm -p 8080:8080 \
	  -v "$(PWD)/checkpoints:/app/checkpoints:ro" \
	  mlops-serve:v1

k8s-train:
	kubectl apply -f k8s/namespace.yaml
	kubectl apply -f k8s/configmap.yaml
	kubectl apply -f k8s/pvc.yaml
	kubectl apply -f k8s/training-job.yaml

k8s-serve:
	kubectl apply -f k8s/serving-deployment.yaml
	kubectl apply -f k8s/serving-service.yaml
	kubectl apply -f k8s/hpa.yaml

k8s-status:
	kubectl get pods,pvc,jobs,deployments,services,hpa -n ml-training
