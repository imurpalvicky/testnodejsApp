#!/bin/bash

# Jenkins credentials and URL
JENKINS_URL="http://<jenkins-url>"
JOB_NAME="<job-name>"
USER="<username>"
API_TOKEN="<api-token>"

# Optional: If CSRF protection is enabled, fetch the crumb token
CRUMB=$(curl -s "$JENKINS_URL/crumbIssuer/api/xml?xpath=concat(//crumbRequestField,\":\",//crumb)" \
    --user $USER:$API_TOKEN)

# Step 1: Trigger the Jenkins job and get the queue item URL
trigger_response=$(curl -s -X POST "$JENKINS_URL/job/$JOB_NAME/build" \
    --user $USER:$API_TOKEN \
    -H "$CRUMB")

if [ $? -ne 0 ]; then
  echo "Failed to trigger the Jenkins job"
  exit 1
fi

# Step 2: Get the queue item URL
queue_item_url=$(curl -s "$JENKINS_URL/job/$JOB_NAME/api/json?tree=queueItemUrl" \
    --user $USER:$API_TOKEN | jq -r '.queueItemUrl')

if [ -z "$queue_item_url" ]; then
  echo "Failed to retrieve the queue item URL."
  exit 1
fi

echo "Job added to the queue: $queue_item_url"

# Step 3: Poll the queue to wait for the job to leave the queue and start building
while :; do
  queue_status=$(curl -s "$queue_item_url/api/json" \
    --user $USER:$API_TOKEN | jq -r '.executable')

  if [ "$queue_status" != "null" ]; then
    build_number=$(echo "$queue_status" | jq -r '.number')
    echo "Job started building. Build number: $build_number"
    break
  else
    echo "Job is still in the queue. Waiting..."
  fi

  # Sleep for a few seconds before checking again
  sleep 5
done

# Step 4: Poll the build status until it completes
job_status=""
while [ "$job_status" != "SUCCESS" ] && [ "$job_status" != "FAILURE" ]; do
  # Fetch the status of the current build
  status_response=$(curl -s "$JENKINS_URL/job/$JOB_NAME/$build_number/api/json" \
    --user $USER:$API_TOKEN)

  # Extract the build status
  job_status=$(echo $status_response | jq -r '.result')

  if [ "$job_status" == "null" ]; then
    echo "Job is still running..."
  else
    echo "Job status: $job_status"
  fi

  # Sleep for a few seconds before checking again
  sleep 10
done

if [ "$job_status" == "SUCCESS" ]; then
  echo "Job completed successfully!"
else
  echo "Job failed."
fi