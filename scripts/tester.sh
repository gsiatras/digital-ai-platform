kubectl port-forward service/ui-service 8080:8080 -n dena

kubectl rollout restart deployment ui-deployment -n platform
kubectl rollout restart statefulset workerservice -n platform

curl -X POST http://127.0.0.1:8080/jobs/submit \
    -H "Content-Type: application/json" \
    -d '{"input_file": "images.jpeg"}'


curl -X GET "http://127.0.0.1:8080/list_files?bucket_name=models"


96157453-4d32-49d4-ad43-2a160b1202f6_images.jpeg

curl -X POST http://127.0.0.1:8080/upload -F 'file=@images.jpeg'    


curl -X POST http://127.0.0.1:8080/upload_model -F 'file=@yolov10n.pt'    