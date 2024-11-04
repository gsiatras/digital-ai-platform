# Variables
SERVICE_NAME := ui-service
UI_DEPLOYMENT_FILE := kubernetes/deployments/ui-service-deployment.yaml
UI_SERVICE_FILE := kubernetes/services/ui-service.yaml


MINIO_STORAGE_FILE := kubernetes/minio/minio-storage-class.yaml
MINIO_PVC_FILE := kubernetes/minio/minio-pvc.yaml
MINIO_PV_FILE := kubernetes/minio/minio-pv.yaml
MINIO_DEPLOYMENT_FILE := kubernetes/minio/minio-deployment.yaml
MINIO_SERVICE_FILE := kubernetes/services/minio-service.yaml





# Targets
.PHONY: deploy

deploy:
	# kubectl create -f $(MINIO_STORAGE_FILE)
	# kubectl create -f $(MINIO_PV_FILE)
	# kubectl create -f $(MINIO_PVC_FILE)
	kubectl create -f $(MINIO_DEPLOYMENT_FILE)
	kubectl create -f $(MINIO_SERVICE_FILE)
	kubectl create -f $(UI_DEPLOYMENT_FILE)
	kubectl create -f $(UI_SERVICE_FILE)
	



.PHONY: clean

clean:
	kubectl delete -f $(UI_DEPLOYMENT_FILE)
	kubectl delete -f $(UI_SERVICE_FILE)
	kubectl delete -f $(AUTH_DEPLOYMENT_FILE)
	kubectl delete -f $(AUTH_SERVICE_FILE)
	kubectl delete -f $(CASSANDRA_DEPLOYMENT_FILE)
	kubectl delete -f $(CASSANDRA_SERVICE_FILE)
	# kubectl delete -f $(CASSANDRA_STORAGE_FILE)
	kubectl delete -f $(MINIO_DEPLOYMENT_FILE)
	kubectl delete -f $(MINIO_PVC_FILE)
	kubectl delete -f $(MINIO_PV_FILE)
	kubectl delete -f $(MINIO_STORAGE_FILE)
	kubectl delete -f $(MINIO_SERVICE_FILE)
	kubectl delete -f $(MANAGER_SERVICE_FILE)
	kubectl delete -f $(MANAGER_DEPLOYMENT_FILE)
	kubectl delete -f $(ROLES_CREATE_FILE)
	kubectl delete -f $(ROLES_ROLESBIND)