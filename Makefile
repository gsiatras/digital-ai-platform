# Variables
SERVICE_NAME := ui-service
UI_DEPLOYMENT_FILE := kubernetes/deployments/ui-service-deployment.yaml
UI_SERVICE_FILE := kubernetes/services/ui-service.yaml

MINIO_STORAGE_FILE := kubernetes/minio/minio-storage-class.yaml
MINIO_PVC_FILE := kubernetes/minio/minio-pvc.yaml
MINIO_PV_FILE := kubernetes/minio/minio-pv.yaml
MINIO_DEPLOYMENT_FILE := kubernetes/minio/minio-deployment.yaml
MINIO_SERVICE_FILE := kubernetes/services/minio-service.yaml

WORKER_SERVICE_DEPLOYMENT_FILE := kubernetes/deployments/worker-service-deployment.yaml
WORKER_SERVICE_FILE := kubernetes/services/worker-service.yaml

MANAGER_SERVICE_DEPLOYMENT_FILE := kubernetes/deployments/manager-service-deployment.yaml
MANAGER_SERVICE_FILE := kubernetes/services/manager-service.yaml

POSTGRES_PVC_FILE := kubernetes/postgres/postgres-pvc.yaml
POSTGRES_CONFIGMAP_FILE := kubernetes/postgres/postgres-configmap.yaml
POSTGRES_DEPLOYMENT_FILE := kubernetes/postgres/postgres-deployment.yaml
POSTGRES_SERVICE_FILE := kubernetes/postgres/postgres-service.yaml

ROLES_CREATE_FILE := kubernetes/roles/job-creator-role.yaml
JOB_LIST_FILE := kubernetes/roles/list-pods-role.yaml
ROLES_ROLESBIND := kubernetes/roles/job-creator-rolebinding.yaml

NAMESPACE := platform



.PHONY: deploy
deploy:
	@echo "Deploying resources..."

	# Create namespace if it doesn't exist
	@kubectl get namespace $(NAMESPACE) > /dev/null 2>&1 || kubectl create namespace $(NAMESPACE)

	# Deploy Minio if not already deployed
	@if ! kubectl get deployment minio-deployment --namespace $(NAMESPACE) > /dev/null 2>&1; then \
		echo "Deploying Minio..."; \
		kubectl create -f $(MINIO_STORAGE_FILE); \
		kubectl create -f $(MINIO_PV_FILE); \
		kubectl create -f $(MINIO_PVC_FILE); \
		kubectl create -f $(MINIO_DEPLOYMENT_FILE); \
		kubectl create -f $(MINIO_SERVICE_FILE); \
	else \
		echo "Minio is already deployed."; \
	fi

	# Deploy PostgreSQL if not already deployed
	@if ! kubectl get deployment postgres-deployment --namespace $(NAMESPACE) > /dev/null 2>&1; then \
		echo "Deploying PostgreSQL..."; \
		kubectl create -f $(POSTGRES_PVC_FILE); \
		kubectl create -f $(POSTGRES_CONFIGMAP_FILE); \
		kubectl create -f $(POSTGRES_DEPLOYMENT_FILE); \
		kubectl create -f $(POSTGRES_SERVICE_FILE); \
	else \
		echo "PostgreSQL is already deployed."; \
	fi

	# Deploy UI service if not already deployed
	@if ! kubectl get deployment ui-deployment --namespace $(NAMESPACE) > /dev/null 2>&1; then \
		echo "Deploying UI service..."; \
		kubectl create -f $(UI_DEPLOYMENT_FILE); \
		kubectl create -f $(UI_SERVICE_FILE); \
	else \
		echo "UI service is already deployed."; \
	fi

	# Deploy Worker services if not already deployed
	@if ! kubectl get statefulset worker-a --namespace $(NAMESPACE) > /dev/null 2>&1; then \
		echo "Deploying Worker services (A, B, C)..."; \
		kubectl create -f $(WORKER_SERVICE_DEPLOYMENT_FILE); \
		kubectl create -f $(WORKER_SERVICE_FILE); \
	else \
		echo "Worker services are already deployed."; \
	fi

	# Deploy Manager service if not already deployed
	@if ! kubectl get statefulset manager-service --namespace $(NAMESPACE) > /dev/null 2>&1; then \
		echo "Deploying Manager service..."; \
		kubectl create -f $(MANAGER_SERVICE_DEPLOYMENT_FILE); \
		kubectl create -f $(MANAGER_SERVICE_FILE); \
	else \
		echo "Manager service is already deployed."; \
	fi

	# Create additional roles
	@if ! kubectl get role pod-lister-role --namespace $(NAMESPACE) > /dev/null 2>&1; then \
		echo "Creating roles..."; \
		kubectl create -f $(JOB_LIST_FILE); \
	else \
		echo "pod-lister-role already exists."; \
	fi

	# Create Roles if not already created
	@if ! kubectl get role job-creator-role --namespace $(NAMESPACE) > /dev/null 2>&1; then \
		echo "Creating roles..."; \
		kubectl create -f $(ROLES_CREATE_FILE); \
		kubectl create -f $(ROLES_ROLESBIND); \
	else \
		echo "job-creator-role already exists."; \
	fi



.PHONY: clean
clean:
	@echo "Cleaning up resources..."

	# Delete UI service if exists
	@if kubectl get deployment ui-deployment --namespace $(NAMESPACE) > /dev/null 2>&1; then \
		echo "Deleting UI service resources..."; \
		kubectl delete -f $(UI_DEPLOYMENT_FILE); \
		kubectl delete -f $(UI_SERVICE_FILE); \
	else \
		echo "UI service resources do not exist."; \
	fi

	# Delete Minio resources if exists
	@if kubectl get deployment minio-deployment --namespace $(NAMESPACE) > /dev/null 2>&1; then \
		echo "Deleting Minio resources..."; \
		kubectl delete -f $(MINIO_DEPLOYMENT_FILE); \
		kubectl delete -f $(MINIO_SERVICE_FILE); \
		kubectl delete -f $(MINIO_PVC_FILE); \
		kubectl delete -f $(MINIO_PV_FILE); \
		kubectl delete -f $(MINIO_STORAGE_FILE); \
	else \
		echo "Minio resources do not exist."; \
	fi

	# Delete PostgreSQL resources if exists
	@if kubectl get deployment postgres-deployment --namespace $(NAMESPACE) > /dev/null 2>&1; then \
		echo "Deleting PostgreSQL resources..."; \
		kubectl delete -f $(POSTGRES_DEPLOYMENT_FILE); \
		kubectl delete -f $(POSTGRES_SERVICE_FILE); \
		kubectl delete -f $(POSTGRES_PVC_FILE); \
		kubectl delete -f $(POSTGRES_CONFIGMAP_FILE); \
	else \
		echo "PostgreSQL resources do not exist."; \
	fi

	# Delete Manager service if exists
	@if kubectl get statefulset manager-service --namespace $(NAMESPACE) > /dev/null 2>&1; then \
		echo "Deleting Manager service resources..."; \
		kubectl delete -f $(MANAGER_SERVICE_FILE); \
		kubectl delete -f $(MANAGER_SERVICE_DEPLOYMENT_FILE); \
	else \
		echo "Manager service resources do not exist."; \
	fi

	# Delete Worker services if exists
	@if kubectl get statefulset worker-a --namespace $(NAMESPACE) > /dev/null 2>&1; then \
		echo "Deleting Worker service resources..."; \
		kubectl delete -f $(WORKER_SERVICE_FILE); \
		kubectl delete -f $(WORKER_SERVICE_DEPLOYMENT_FILE); \
	else \
		echo "Worker service resources do not exist."; \
	fi

	# Delete roles if exist
	@if kubectl get role job-creator-role --namespace $(NAMESPACE) > /dev/null 2>&1; then \
		echo "Deleting roles..."; \
		kubectl delete -f $(ROLES_CREATE_FILE); \
		kubectl delete -f $(ROLES_ROLESBIND); \
	else \
		echo "job-creator-role does not exist."; \
	fi

	@if kubectl get role pod-lister-role --namespace $(NAMESPACE) > /dev/null 2>&1; then \
		echo "Deleting roles..."; \
		kubectl delete -f $(JOB_LIST_FILE); \
	else \
		echo "pod-lister-role does not exist."; \
	fi
