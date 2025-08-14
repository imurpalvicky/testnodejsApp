import csv
import os
import pandas as pd
import requests
import json
import base64
from urllib.parse import urlparse
import tempfile
import subprocess
import shutil

class GitHubRepoScanner:
    def __init__(self, github_token=None, temp_dir=None):
        """
        Initialize the GitHub repository scanner.
        
        Args:
            github_token (str, optional): GitHub personal access token for API access
            temp_dir (str, optional): Directory for temporary clones (if using git clone method)
        """
        self.github_token = github_token
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.headers = {}
        
        if self.github_token:
            self.headers['Authorization'] = f'token {github_token}'
            self.headers['Accept'] = 'application/vnd.github.v3+json'
    
    def parse_github_url(self, url):
        """
        Parse GitHub URL to extract owner and repository name.
        
        Args:
            url (str): GitHub repository URL
            
        Returns:
            tuple: (base_url, owner, repo_name)
        """
        # Handle both github.com and custom GitHub enterprise URLs
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # Remove leading slash and split path
        path_parts = parsed.path.strip('/').split('/')
        
        if len(path_parts) >= 2:
            owner = path_parts[0]
            repo_name = path_parts[1]
            # Remove .git suffix if present
            if repo_name.endswith('.git'):
                repo_name = repo_name[:-4]
            return base_url, owner, repo_name
        else:
            raise ValueError(f"Invalid GitHub URL format: {url}")
    
    def scan_repo_via_api(self, url):
        """
        Scan repository structure using GitHub API.
        
        Args:
            url (str): GitHub repository URL
            
        Returns:
            list: List of dictionaries containing file/folder information
        """
        try:
            base_url, owner, repo_name = self.parse_github_url(url)
            
            # Construct API URL
            if 'github.com' in base_url:
                api_url = f"https://api.github.com/repos/{owner}/{repo_name}/contents"
            else:
                # GitHub Enterprise
                api_url = f"{base_url}/api/v3/repos/{owner}/{repo_name}/contents"
            
            print(f"Fetching contents from API: {api_url}")
            
            response = requests.get(api_url, headers=self.headers)
            
            if response.status_code == 200:
                contents = response.json()
                results = []
                
                for item in contents:
                    item_type = 'folder' if item['type'] == 'dir' else 'file'
                    item_path = f"{item['name']}/" if item['type'] == 'dir' else item['name']
                    
                    results.append({
                        'repo_name': repo_name,
                        'item_path': item_path,
                        'item_type': item_type,
                        'size': item.get('size', 0) if item['type'] == 'file' else None
                    })
                
                return results
            
            elif response.status_code == 404:
                print(f"Repository not found or private: {url}")
                return [{
                    'repo_name': repo_name,
                    'item_path': 'ERROR: Repository not found or private',
                    'item_type': 'ERROR',
                    'size': None
                }]
            
            elif response.status_code == 403:
                print(f"Access forbidden (rate limited or private): {url}")
                return [{
                    'repo_name': repo_name,
                    'item_path': 'ERROR: Access forbidden or rate limited',
                    'item_type': 'ERROR',
                    'size': None
                }]
            
            else:
                print(f"API request failed with status {response.status_code}: {url}")
                return [{
                    'repo_name': repo_name,
                    'item_path': f'ERROR: API request failed ({response.status_code})',
                    'item_type': 'ERROR',
                    'size': None
                }]
                
        except Exception as e:
            print(f"Error processing {url}: {str(e)}")
            return [{
                'repo_name': url.split('/')[-1] if '/' in url else 'unknown',
                'item_path': f'ERROR: {str(e)}',
                'item_type': 'ERROR',
                'size': None
            }]
    
    def scan_repo_via_clone(self, url):
        """
        Scan repository structure by cloning it temporarily.
        
        Args:
            url (str): GitHub repository URL
            
        Returns:
            list: List of dictionaries containing file/folder information
        """
        try:
            _, owner, repo_name = self.parse_github_url(url)
            clone_path = os.path.join(self.temp_dir, f"temp_clone_{repo_name}")
            
            # Remove existing clone if it exists
            if os.path.exists(clone_path):
                shutil.rmtree(clone_path)
            
            print(f"Cloning repository: {url}")
            
            # Clone the repository
            result = subprocess.run([
                'git', 'clone', '--depth', '1', url, clone_path
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                print(f"Git clone failed: {result.stderr}")
                return [{
                    'repo_name': repo_name,
                    'item_path': f'ERROR: Clone failed - {result.stderr}',
                    'item_type': 'ERROR',
                    'size': None
                }]
            
            # Scan the cloned repository
            results = []
            root_items = os.listdir(clone_path)
            
            for item in root_items:
                # Skip .git directory
                if item == '.git':
                    continue
                    
                item_path = os.path.join(clone_path, item)
                
                if os.path.isdir(item_path):
                    results.append({
                        'repo_name': repo_name,
                        'item_path': f"{item}/",
                        'item_type': 'folder',
                        'size': None
                    })
                else:
                    file_size = os.path.getsize(item_path)
                    results.append({
                        'repo_name': repo_name,
                        'item_path': item,
                        'item_type': 'file',
                        'size': file_size
                    })
            
            # Clean up the cloned repository
            shutil.rmtree(clone_path)
            
            return results
            
        except subprocess.TimeoutExpired:
            print(f"Clone timeout for repository: {url}")
            return [{
                'repo_name': repo_name,
                'item_path': 'ERROR: Clone timeout',
                'item_type': 'ERROR',
                'size': None
            }]
        except Exception as e:
            print(f"Error cloning {url}: {str(e)}")
            return [{
                'repo_name': url.split('/')[-1] if '/' in url else 'unknown',
                'item_path': f'ERROR: {str(e)}',
                'item_type': 'ERROR',
                'size': None
            }]
    
    def scan_repositories_from_csv(self, input_csv_path, output_csv_path, method='api'):
        """
        Scan repositories listed in a CSV file and extract root folders and files.
        
        Args:
            input_csv_path (str): Path to the input CSV file containing repository URLs
            output_csv_path (str): Path to the output CSV file
            method (str): 'api' for GitHub API, 'clone' for git clone method
        """
        all_results = []
        
        try:
            # Read the input CSV file
            df = pd.read_csv(input_csv_path)
            
            # Try to find URL column
            url_column = None
            possible_columns = ['url', 'repo_url', 'repository_url', 'github_url', 'link']
            
            for col in possible_columns:
                if col in df.columns:
                    url_column = col
                    break
            
            if url_column is None:
                # Use the first column
                url_column = df.columns[0]
                print(f"Warning: Using '{url_column}' as URL column")
            
            print(f"Processing {len(df)} repositories using {method} method...")
            
            # Process each repository
            for index, row in df.iterrows():
                repo_url = row[url_column].strip()
                print(f"\nProcessing ({index+1}/{len(df)}): {repo_url}")
                
                if method == 'api':
                    results = self.scan_repo_via_api(repo_url)
                elif method == 'clone':
                    results = self.scan_repo_via_clone(repo_url)
                else:
                    raise ValueError("Method must be 'api' or 'clone'")
                
                all_results.extend(results)
        
        except Exception as e:
            print(f"Error reading input CSV file: {str(e)}")
            return
        
        # Write results to output CSV
        try:
            results_df = pd.DataFrame(all_results)
            results_df.to_csv(output_csv_path, index=False)
            print(f"\nResults saved to: {output_csv_path}")
            print(f"Total items found: {len(all_results)}")
            
            # Print summary
            if all_results:
                summary = results_df.groupby(['repo_name', 'item_type']).size().unstack(fill_value=0)
                print("\nSummary by repository:")
                print(summary)
                
        except Exception as e:
            print(f"Error writing output CSV file: {str(e)}")

def create_sample_input_csv(file_path):
    """
    Creates a sample input CSV file for testing.
    
    Args:
        file_path (str): Path where to create the sample CSV
    """
    sample_data = {
        'repo_url': [
            'https://github.test.com/orgname/repo1',
            'https://github.test.com/orgname/repo2',
            'https://github.com/octocat/Hello-World',
        ]
    }
    
    df = pd.DataFrame(sample_data)
    df.to_csv(file_path, index=False)
    print(f"Sample input CSV created at: {file_path}")

if __name__ == "__main__":
    # Configuration
    input_csv_file = "github_repositories.csv"
    output_csv_file = "repository_structure.csv"
    
    # GitHub token (optional but recommended for higher rate limits)
    # You can set this as an environment variable: export GITHUB_TOKEN="your_token_here"
    github_token = os.environ.get('GITHUB_TOKEN')
    
    # Initialize scanner
    scanner = GitHubRepoScanner(github_token=github_token)
    
    # Create sample input if it doesn't exist
    if not os.path.exists(input_csv_file):
        print(f"Input file {input_csv_file} not found. Creating a sample file...")
        create_sample_input_csv(input_csv_file)
        print(f"Please edit {input_csv_file} with your actual repository URLs and run the script again.")
    else:
        # Choose method: 'api' (faster, requires less resources) or 'clone' (more reliable for private repos)
        method = 'api'  # Change to 'clone' if you prefer git clone method
        
        if github_token:
            print("Using GitHub token for API access")
        else:
            print("No GitHub token provided. Rate limiting may apply.")
            print("Set GITHUB_TOKEN environment variable for higher limits.")
        
        # Run the scanner
        scanner.scan_repositories_from_csv(input_csv_file, output_csv_file, method=method)

# Example of direct usage:
"""
# Direct usage example:
scanner = GitHubRepoScanner(github_token="your_token_here")
repos = [
    "https://github.test.com/orgname/repo1",
    "https://github.test.com/orgname/repo2"
]

all_results = []
for repo_url in repos:
    results = scanner.scan_repo_via_api(repo_url)  # or scan_repo_via_clone
    all_results.extend(results)

# Save to CSV
df = pd.DataFrame(all_results)
df.to_csv("output.csv", index=False)
"""
