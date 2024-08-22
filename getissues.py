import requests

# Replace with your GitHub token
GITHUB_TOKEN = 'your_github_token'
HEADERS = {"Authorization": f"Bearer {GITHUB_TOKEN}"}

# GraphQL query
QUERY = """
query($searchQuery: String!) {
  search(query: $searchQuery, type: ISSUE, first: 10) {
    edges {
      node {
        ... on Issue {
          id
          body
          state
          closedBy {
            login
          }
          comments(first: 10) {
            edges {
              node {
                body
                author {
                  login
                }
                createdAt
              }
            }
          }
        }
      }
    }
  }
}
"""

def build_search_query(labels, repo):
    # Construct the search query string with dynamic labels
    labels_query = ' '.join([f'label:{label}' for label in labels])
    return f"{labels_query} repo:{repo}"

def run_query(query, variables):
    request = requests.post('https://api.github.com/graphql', json={'query': query, 'variables': variables}, headers=HEADERS)
    if request.status_code == 200:
        return request.json()
    else:
        raise Exception(f"Query failed to run with status code {request.status_code}. {request.text}")

def extract_issue_data(issue_node):
    # Extract comments
    comments = []
    for comment in issue_node['comments']['edges']:
        comment_node = comment['node']
        comments.append({
            "body": comment_node['body'],
            "author": comment_node['author']['login'],
            "createdAt": comment_node['createdAt']
        })
    
    # Build issue object
    issue_data = {
        "issue_id": issue_node['id'],
        "issue_body": issue_node['body'],
        "issue_status": issue_node['state'],
        "closed_by": issue_node['closedBy']['login'] if issue_node['closedBy'] else None,
        "comments": comments
    }
    
    return issue_data

def main(labels, repo):
    # Build the search query with dynamic labels
    search_query = build_search_query(labels, repo)
    variables = {"searchQuery": search_query}
    
    # Run the query
    result = run_query(QUERY, variables)
    
    # Extract and print the issue information in the desired format
    issues = result['data']['search']['edges']
    
    issues_data = []
    for issue in issues:
        issue_node = issue['node']
        issue_data = extract_issue_data(issue_node)
        issues_data.append(issue_data)
    
    # Print or return the issues data
    for issue in issues_data:
        print(issue)
        print("="*80)
    
    # If you want to return it instead of printing
    # return issues_data

if __name__ == "__main__":
    # Example usage with dynamic labels and repository
    labels = ['x', 'y']  # Replace with your dynamic label values
    repo = 'your_org/your_repo'  # Replace with your organization/repository
    
    main(labels, repo)
