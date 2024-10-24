import requests
import csv

# Replace these with your GitHub token and org name
GITHUB_TOKEN = 'your_github_token'
ORG_NAME = 'your_org_name'
API_URL = 'https://api.github.com/graphql'

HEADERS = {
    'Authorization': f'bearer {GITHUB_TOKEN}',
    'Content-Type': 'application/json'
}

def run_query(query, variables=None):
    response = requests.post(API_URL, json={'query': query, 'variables': variables}, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Query failed with status code {response.status_code}: {response.text}")

def get_paginated_repos(org_name):
    """Retrieve all repositories in the organization using pagination."""
    repos = []
    end_cursor = None
    has_next_page = True

    while has_next_page:
        query = """
        query($orgName: String!, $after: String) {
          organization(login: $orgName) {
            repositories(first: 100, after: $after) {
              nodes {
                name
                owner {
                  login
                }
                workflowRuns(first: 10) {
                  nodes {
                    id
                    status
                    environment {
                      name
                    }
                  }
                  pageInfo {
                    hasNextPage
                    endCursor
                  }
                }
              }
              pageInfo {
                hasNextPage
                endCursor
              }
            }
          }
        }
        """
        variables = {"orgName": org_name, "after": end_cursor}
        result = run_query(query, variables)

        # Add repositories to the list
        repo_nodes = result['data']['organization']['repositories']['nodes']
        repos.extend(repo_nodes)

        # Handle pagination
        page_info = result['data']['organization']['repositories']['pageInfo']
        has_next_page = page_info['hasNextPage']
        end_cursor = page_info['endCursor']

    return repos

def get_paginated_workflows(repo_full_name, workflows_info):
    """Handle workflow pagination for a given repository."""
    workflows = workflows_info['nodes']
    end_cursor = workflows_info['pageInfo']['endCursor']
    has_next_page = workflows_info['pageInfo']['hasNextPage']

    while has_next_page:
        query = """
        query($repoName: String!, $after: String) {
          repository(name: $repoName) {
            workflowRuns(first: 10, after: $after) {
              nodes {
                id
                status
                environment {
                  name
                }
              }
              pageInfo {
                hasNextPage
                endCursor
              }
            }
          }
        }
        """
        variables = {"repoName": repo_full_name, "after": end_cursor}
        result = run_query(query, variables)

        workflow_nodes = result['data']['repository']['workflowRuns']['nodes']
        workflows.extend(workflow_nodes)

        # Handle pagination for workflow runs
        page_info = result['data']['repository']['workflowRuns']['pageInfo']
        has_next_page = page_info['hasNextPage']
        end_cursor = page_info['endCursor']

    return workflows

def find_waiting_workflows():
    repos = get_paginated_repos(ORG_NAME)
    waiting_workflows = []
    
    for repo in repos:
        repo_name = f"{repo['owner']['login']}/{repo['name']}"
        print(f"Checking repo: {repo_name}")
        
        workflow_runs_info = repo.get('workflowRuns', {})
        workflows = get_paginated_workflows(repo_name, workflow_runs_info)
        
        for workflow in workflows:
            if workflow['status'] == 'QUEUED' or workflow['status'] == 'WAITING':
                waiting_workflows.append({
                    'repo': repo_name,
                    'workflow_id': workflow['id'],
                    'status': workflow['status'],
                    'environment': workflow.get('environment', {}).get('name')
                })
    
    return waiting_workflows

def save_to_csv(workflows, filename="waiting_workflows.csv"):
    """Save the workflow data to a CSV file."""
    with open(filename, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['Repo', 'Workflow ID', 'Status', 'Environment'])
        writer.writeheader()
        for workflow in workflows:
            writer.writerow({
                'Repo': workflow['repo'],
                'Workflow ID': workflow['workflow_id'],
                'Status': workflow['status'],
                'Environment': workflow['environment'] or 'None'  # Handle None environments
            })

def main():
    waiting_workflows = find_waiting_workflows()
    
    if waiting_workflows:
        print("Found workflows in a waiting or queued state:")
        for workflow in waiting_workflows:
            print(f"Repo: {workflow['repo']}, Workflow ID: {workflow['workflow_id']}, Status: {workflow['status']}, Environment: {workflow['environment']}")
        
        # Save the results to a CSV file
        save_to_csv(waiting_workflows)
        print("Results saved to 'waiting_workflows.csv'")
    else:
        print("No workflows in waiting or queued state found.")

if __name__ == '__main__':
    main()
