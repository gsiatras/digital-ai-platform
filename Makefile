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

ROLES_CREATE_FILE := kubernetes/roles/job-creator-role.yaml
JOB_LIST_FILE := kubernetes/roles/list-pods-role.yaml
ROLES_ROLESBIND := kubernetes/roles/job-creator-rolebinding.yaml

NAMESPACE := platform

# Check if resource exists
define check_resource_exists
	$(shell kubectl get $(1) $(2) --namespace $(3) > /dev/null 2>&1 && echo "true" || echo "false")
endef



.PHONY: deploy
deploy:
	@echo "Deploying resources..."
	
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

	# Deploy UI service if not already deployed
	@if ! kubectl get deployment ui-deployment --namespace $(NAMESPACE) > /dev/null 2>&1; then \
		echo "Deploying UI service..."; \
		kubectl create -f $(UI_DEPLOYMENT_FILE); \
		kubectl create -f $(UI_SERVICE_FILE); \
	else \
		echo "UI service is already deployed."; \
	fi

	# Deploy Worker service if not already deployed
	@if ! kubectl get statefulset worker-service --namespace $(NAMESPACE) > /dev/null 2>&1; then \
		echo "Deploying Worker service..."; \
		kubectl create -f $(WORKER_SERVICE_DEPLOYMENT_FILE); \
		kubectl create -f $(WORKER_SERVICE_FILE); \
	else \
		echo "Worker service is already deployed."; \
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
		echo "Roles do not exist."; \
	fi
	
	# Create Roles if not already created
	@if ! kubectl get role job-creator-role --namespace $(NAMESPACE) > /dev/null 2>&1; then \
		echo "Creating roles..."; \
		kubectl create -f $(ROLES_CREATE_FILE); \
		kubectl create -f $(ROLES_ROLESBIND); \
	else \
		echo "Roles already exist."; \
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

	# Delete Manager service if exists
	@if kubectl get statefulset manager-service --namespace $(NAMESPACE) > /dev/null 2>&1; then \
		echo "Deleting Manager service resources..."; \
		kubectl delete -f $(MANAGER_SERVICE_FILE); \
		kubectl delete -f $(MANAGER_SERVICE_DEPLOYMENT_FILE); \
	else \
		echo "Manager service resources do not exist."; \
	fi

	# Delete Worker service if exists
	@if kubectl get statefulset worker-service --namespace $(NAMESPACE) > /dev/null 2>&1; then \
		echo "Deleting Worker service resources..."; \
		kubectl delete -f $(WORKER_SERVICE_FILE); \
		kubectl delete -f $(WORKER_SERVICE_DEPLOYMENT_FILE); \
	else \
		echo "Worker service resources do not exist."; \
	fi

	# Delete any additional roles if exists
	@if kubectl get role job-creator-role --namespace $(NAMESPACE) > /dev/null 2>&1; then \
		echo "Deleting roles..."; \
		kubectl delete -f $(ROLES_CREATE_FILE); \
		kubectl delete -f $(ROLES_ROLESBIND); \
	else \
		echo "Roles do not exist."; \
	fi


	# Delete any additional roles if exists
	@if kubectl get role pod-lister-role --namespace $(NAMESPACE) > /dev/null 2>&1; then \
		echo "Deleting roles..."; \
		kubectl delete -f $(JOB_LIST_FILE); \
	else \
		echo "Roles do not exist."; \
	fi
