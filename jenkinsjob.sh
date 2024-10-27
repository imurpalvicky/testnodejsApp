#!/bin/bash

# Jenkins credentials and URL
JENKINS_URL="http://<jenkins-url>"
JOB_NAME="<job-name>"
USER="<username>"
API_TOKEN="<api-token>"

# Optional: If CSRF protection is enabled, fetch the crumb token
CRUMB=$(curl -s "$JENKINS_URL/crumbIssuer/api/xml?xpath=concat(//crumbRequestField,\":\",//crumb)" \
    --user $USER:$API_TOKEN)

# Trigger the Jenkins job and get the queue ID
trigger_response=$(curl -s -X POST "$JENKINS_URL/job/$JOB_NAME/build" \
    --user $USER:$API_TOKEN \
    -H "$CRUMB")

if [ $? -ne 0 ]; then
  echo "Failed to trigger the Jenkins job"
  exit 1
fi

# Retrieve the queue ID
queue_id=$(curl -s "$JENKINS_URL/job/$JOB_NAME/api/json?tree=queueItemId" \
    --user $USER:$API_TOKEN | jq -r '.queueItemId')

echo "Job queued with Queue ID: $queue_id"

# Step 3: Poll the queue with shorter intervals
build_number=""
poll_interval=1  # Polling every 1 second to minimize timing issues
max_retries=10   # Maximum retries to ensure we don’t miss the transition

for ((i=1; i<=max_retries; i++)); do
  queue_status=$(curl -s "$JENKINS_URL/queue/item/$queue_id/api/json" \
    --user $USER:$API_TOKEN)

  # Check if the job has started building
  build_number=$(echo "$queue_status" | jq -r '.executable.number // empty')

  if [ -n "$build_number" ]; then
    echo "Job started building with Build Number: $build_number"
    break
  fi

  # If we've exceeded retries, exit with error
  if [ $i -eq $max_retries ]; then
    echo "Failed to detect build number, queue item may have been missed."
    exit 1
  fi

  echo "Job is still in the queue. Waiting..."
  sleep $poll_interval
done

# Step 4: Monitor the build status until completion
job_status=""
while [ "$job_status" != "SUCCESS" ] && [ "$job_status" != "FAILURE" ]; do
  status_response=$(curl -s "$JENKINS_URL/job/$JOB_NAME/$build_number/api/json" \
    --user $USER:$API_TOKEN)

  job_status=$(echo $status_response | jq -r '.result')

  if [ "$job_status" == "null" ]; then
    echo "Job is still running..."
  else
    echo "Job status: $job_status"
  fi

  sleep 10
done

if [ "$job_status" == "SUCCESS" ]; then
  echo "Job completed successfully!"
else
  echo "Job failed."
fi