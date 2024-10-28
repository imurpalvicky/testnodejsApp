#!/bin/bash

# Define the search query parameters
SEARCH_QUERY="assignment_group"
FILE_TYPE="properties"
OUTPUT_FILE="repositories.csv"
GITHUB_TOKEN="your_github_token_here"  # Replace with your actual GitHub token
ORG="your_org_name_here"               # Replace with the GitHub org or user if you want to narrow the search

# GitHub Search API URL
API_URL="https://api.github.com/search/code"

# Create or clear the output file
echo "Repository Name" > "$OUTPUT_FILE"

# Fetch results and extract repository names
curl -s -H "Authorization: token $GITHUB_TOKEN" \
     "$API_URL?q=$SEARCH_QUERY+in:file+extension:$FILE_TYPE+user:$ORG" |
jq -r '.items[].repository.full_name' |
sort -u |    # Sort and remove duplicate repo names
while read -r repo; do
    echo "$repo"
    echo "$repo" >> "$OUTPUT_FILE"
done

echo "Repository names saved to $OUTPUT_FILE"


