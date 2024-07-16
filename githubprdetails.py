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
    all_prs = []

    for repository in repositories:
        print(f"Repository: {repository}")
        pull_requests = fetch_all_pull_requests(repository)
        
        # Filter pull requests by date range
        filtered_pull_requests = filter_pull_requests(pull_requests, start_date, end_date)
        
        for pr in filtered_pull_requests:
            pr_details = {
                "repo_name": repository,
                "title": pr['title'],
                "created_at": pr['createdAt'],
                "state": pr['state'],
                "closed_at": pr['closedAt'],
                "base_branch": pr['baseRefName'],
                "head_branch": pr['headRefName'],
                "author": pr['author']['login'],
                "labels": [label['name'] for label in pr['labels']['nodes']],
                "comments": [
                    {
                        "comment_author": comment['author']['login'],
                        "comment_body": comment['body'],
                        "comment_created_at": comment['createdAt']
                    }
                    for comment in pr["comments"]["nodes"]
                ]
            }
            all_prs.append(pr_details)
    
    print(json.dumps(all_prs, indent=4))

if __name__ == "__main__":
    main()
