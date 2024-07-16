import requests
import json
from datetime import datetime

# GitHub Personal Access Token
GITHUB_TOKEN = 'YOUR_GITHUB_TOKEN'
ORG_NAME = 'YOUR_ORG_NAME'
HEADERS = {"Authorization": f"Bearer {GITHUB_TOKEN}"}

def run_query(query):
    """Run a GraphQL query and return the json response."""
    request = requests.post('https://api.github.com/graphql', json={'query': query}, headers=HEADERS)
    if request.status_code == 200:
        return request.json()
    else:
        raise Exception(f"Query failed to run by returning code of {request.status_code}. {query}")

def get_repositories(organization, end_cursor=None):
    """Fetch repositories from the organization."""
    cursor_clause = f', after: "{end_cursor}"' if end_cursor else ""
    query = f"""
    {{
        organization(login: "{organization}") {{
            repositories(first: 100{cursor_clause}) {{
                pageInfo {{
                    hasNextPage
                    endCursor
                }}
                nodes {{
                    name
                }}
            }}
        }}
    }}
    """
    return run_query(query)

def get_pull_requests(repository, end_cursor=None):
    """Fetch pull requests from the repository."""
    cursor_clause = f', after: "{end_cursor}"' if end_cursor else ""
    query = f"""
    {{
        repository(owner: "{ORG_NAME}", name: "{repository}") {{
            pullRequests(first: 100{cursor_clause}) {{
                pageInfo {{
                    hasNextPage
                    endCursor
                }}
                nodes {{
                    title
                    createdAt
                    state
                    closedAt
                    baseRefName
                    headRefName
                    author {{
                        login
                    }}
                    labels(first: 10) {{
                        nodes {{
                            name
                        }}
                    }}
                    comments(first: 100) {{
                        nodes {{
                            body
                            createdAt
                            author {{
                                login
                            }}
                        }}
                    }}
                }}
            }}
        }}
    }}
    """
    return run_query(query)

def fetch_all_repositories():
    """Fetch all repositories from the organization handling pagination."""
    has_next_page = True
    end_cursor = None
    repositories = []

    while has_next_page:
        result = get_repositories(ORG_NAME, end_cursor)
        repos = result["data"]["organization"]["repositories"]["nodes"]
        repositories.extend([repo["name"] for repo in repos])
        page_info = result["data"]["organization"]["repositories"]["pageInfo"]
        has_next_page = page_info["hasNextPage"]
        end_cursor = page_info["endCursor"]

    return repositories

def fetch_all_pull_requests(repository):
    """Fetch all pull requests from a repository handling pagination."""
    has_next_page = True
    end_cursor = None
    pull_requests = []

    while has_next_page:
        result = get_pull_requests(repository, end_cursor)
        prs = result["data"]["repository"]["pullRequests"]["nodes"]
        pull_requests.extend(prs)
        page_info = result["data"]["repository"]["pullRequests"]["pageInfo"]
        has_next_page = page_info["hasNextPage"]
        end_cursor = page_info["endCursor"]

    return pull_requests

def filter_pull_requests(pull_requests, start_date, end_date):
    """Filter pull requests based on creation and closing dates."""
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")

    filtered_prs = []
    for pr in pull_requests:
        created_at = datetime.strptime(pr['createdAt'], "%Y-%m-%dT%H:%M:%SZ")
        closed_at = pr['closedAt']
        if closed_at:
            closed_at = datetime.strptime(closed_at, "%Y-%m-%dT%H:%M:%SZ")
        
        if start_date <= created_at <= end_date or (closed_at and start_date <= closed_at <= end_date):
            filtered_prs.append(pr)
    
    return filtered_prs

def main():
    # Define the date range for filtering
    start_date = "2023-01-01"
    end_date = "2023-12-31"

    repositories = fetch_all_repositories()

    for repository in repositories:
        print(f"Repository: {repository}")
        pull_requests = fetch_all_pull_requests(repository)
        
        # Filter pull requests by date range
        filtered_pull_requests = filter_pull_requests(pull_requests, start_date, end_date)
        
        for pr in filtered_pull_requests:
            print(f"  PR Title: {pr['title']}")
            print(f"  Created At: {pr['createdAt']}")
            print(f"  State: {pr['state']}")
            print(f"  Closed At: {pr['closedAt']}")
            print(f"  Base Branch: {pr['baseRefName']}")
            print(f"  Head Branch: {pr['headRefName']}")
            print(f"  Author: {pr['author']['login']}")
            print(f"  Labels: {[label['name'] for label in pr['labels']['nodes']]}")
            for comment in pr["comments"]["nodes"]:
                print(f"    Comment Author: {comment['author']['login']}")
                print(f"    Comment Body: {comment['body']}")
                print(f"    Comment Created At: {comment['createdAt']}")

if __name__ == "__main__":
    main()
