import csv
import requests
from urllib.parse import urlparse
import os

# Personal Access Token (store in env var for safety)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("Please set GITHUB_TOKEN environment variable.")

# GitHub Enterprise base API URL
API_BASE = "https://github.test.com/api/v3"

INPUT_CSV = "repos.csv"
OUTPUT_CSV = "repo_root_contents.csv"

def parse_repo_url(url):
    """Extract org and repo name from HTML URL."""
    parts = urlparse(url).path.strip("/").split("/")
    if len(parts) < 2:
        raise ValueError(f"Invalid repo URL: {url}")
    return parts[-2], parts[-1]  # org, repo

def get_root_contents(org, repo):
    """Fetch root folder contents from GitHub API."""
    api_url = f"{API_BASE}/repos/{org}/{repo}/contents/"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    resp = requests.get(api_url, headers=headers)
    if resp.status_code != 200:
        print(f"Failed to fetch {org}/{repo}: {resp.status_code} {resp.text}")
        return []
    data = resp.json()
    return [item["name"] for item in data]

def main():
    results = []

    # Read repo list from CSV
    with open(INPUT_CSV, newline="", encoding="utf-8") as infile:
        reader = csv.reader(infile)
        for row in reader:
            repo_url = row[0].strip()
            if not repo_url:
                continue

            try:
                org, repo = parse_repo_url(repo_url)
            except ValueError as e:
                print(e)
                continue

            print(f"Fetching root contents for {org}/{repo}...")
            items = get_root_contents(org, repo)
            for item in items:
                results.append([repo, item])

    # Write results to CSV
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(["repo_name", "rootfolder/filename"])
        writer.writerows(results)

    print(f"Done! Output saved to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
