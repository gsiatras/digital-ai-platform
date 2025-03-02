##################################### TESTING #############################################

curl -X GET http://127.0.0.1:8080/list_models
curl -X GET http://127.0.0.1:8080/routes
curl -X POST -F "file=@/Users/gsiatras/Documents/Ptyxiaki/digital-ai-platform/yolov10n.pt" http://127.0.0.1:8080/upload_model 
curl -X GET 'http://127.0.0.1:8080/list_files?bucket_name=result-files'   

curl -X POST -H "Content-Type: application/json" -d '{"model_id": "yolov10n"}' http://127.0.0.1:8080/load_model

curl -X POST -F "file=@/Users/gsiatras/Documents/Ptyxiaki/digital-ai-platform/images/images.jpeg" http://127.0.0.1:8080/upload 
curl -X POST http://127.0.0.1:8080/jobs/submit \
-H "Content-Type: application/json" \
-d '{
    "input_file": "images.jpeg"
}'
curl -o downloaded_file.json "http://127.0.0.1:8080/get_result_file?file_name=d0b901c0-4f15-4af0-b4bc-7ad6c0e18290_results.json"
########################################## k8s ########################################
## RESTARTS
kubectl rollout restart deployment/ui-deployment -n platform
kubectl rollout restart statefulset/worker-service -n platform
kubectl rollout restart statefulset/manager-service -n platform

####OPEN CONNECTIONS
kubectl port-forward service/ui-service 8080:8080 -n platform      

#### DELETE ALL
 kubectl delete all --all -n platform     

#### GET PODS
kubectl get pods -n platform 


### LOGS=
kubectl logs ui-deployment-dd6f94d4-zqshm    -n platform



 ########################################### Docker #####################################
docker build -t digital_platform-ui_service .
docker tag digital_platform-ui_service gsiatras13/digital_platform-ui_service:a1.1
docker push gsiatras13/digital_platform-ui_service:a1.1

###MANAGER####
docker build -t digital_platform-ui_service .
docker tag digital_platform-ui_service gsiatras13/digital_platform-ui_service:a1.1
docker push gsiatras13/digital_platform-ui_service:a1.1