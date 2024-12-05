import sys
import requests
import logging
import time
import json
import pandas as pd
import os

# GitHub Personal Access Token
auth_token = os.getenv('GITHUB_TOKEN')

# setup logging and logging formatting
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


class GitHubAPIClient:
    def __init__(self, auth_token):
        self.base_url = 'https://api.github.com'
        self.headers = {
            'Accept': 'application/vnd.github.v3+json',
            'Authorization': f'Bearer {auth_token}',
            'X-GitHub-Api-Version': '2022-11-28'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    @staticmethod
    def handle_rate_limits(response):
        """Handle rate limiting by checking remaining requests and waiting if rate limit is exceeded"""
        # remaining requests for a particular endpoint
        remaining = int(response.headers.get('X-RateLimit-Remaining', 0))
        if remaining == 0 and response.status_code == 403:
            reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
            sleep_time = max(reset_time - time.time(), 0)
            logger.warning(f'Rate limit nearly exceeded. Waiting for {sleep_time:.2f} seconds')
            time.sleep(sleep_time)

    def paginate_request(self, url, params=None, max_results=None):
        """Handle pagination for requests using links header from response"""
        all_results = []
        while url and (max_results is None or len(all_results) < max_results):
            logger.debug('Retrieving from ' + str(url))
            response = self.session.get(url, params=params)
            self.handle_rate_limits(response)

            # error handling for unsuccessful responses
            if response.status_code != 200:
                error_message = self.handle_error(response)
                logger.error(f'Error sending request to {url} with params {params}: {error_message}')
                sys.exit(1)

            data = response.json()
            if isinstance(data, list):
                all_results.extend(data)
            else:
                all_results.append(data)
            # stop if max_results is reached
            if max_results is not None and len(all_results) >= max_results:
                break
            # get next page url in links header
            url = response.links.get('next', {}).get('url')
            params = None
        return all_results[:max_results] if max_results else all_results

    def search_repositories(self, query, sort='stars', order='desc', per_page=100, max_results=None):
        """Search for repositories which match the search"""
        url = f'{self.base_url}/search/repositories'
        params = {
            'q': query,
            'sort': sort,
            'order': order,
            'per_page': per_page
        }
        return self.paginate_request(url, params, max_results=max_results)

    def get_repository_commits(self, owner, repo, per_page=100, max_results=None):
        """Get commits from a repository"""
        url = f'{self.base_url}/repos/{owner}/{repo}/commits'
        params = {
            'per_page': per_page
        }
        return self.paginate_request(url, params, max_results=max_results)

    def get_repository_contents(self, owner, repo, path=''):
        """Get contents of a repository at a specific path."""
        url = f'{self.base_url}/repos/{owner}/{repo}/contents/{path}'
        return self.paginate_request(url)

    @staticmethod
    def handle_error(response):
        """Handle various API error responses."""
        error_handlers = {
            401: 'Authentication error. Please check your token.',
            403: 'Rate limit exceeded or permission denied.',
            404: 'Resource not found. Verify the URL.',
            422: 'Validation failed. Parameters are incorrect.'
        }
        try:
            error_details = response.json().get('message', 'No additional details provided.')
        except ValueError:  # cases where the response body isn't JSON
            error_details = 'Response body is not valid JSON.'

        return error_handlers.get(response.status_code,
                                  f'Unknown error: {response.status_code}. Error details: {error_details}')


# example usage and demonstration
def main():
    try:
        # initialize client
        client = GitHubAPIClient(auth_token)

        # search repositories example
        max_repos = 5
        logger.info(f'Searching for {'all' if not max_repos else max_repos} pages of repositories with stars > 1000')
        repos = client.search_repositories('stars:>1000', sort='stars', max_results=max_repos)

        # display some repositories
        display_repos(repos)

        # get commits for the first repository
        sample_repo = repos[0]['items'][0]
        owner = sample_repo['owner']['login']
        repo_name = sample_repo['name']

        # limit number of commits to save time
        max_commits = 10
        logger.info(f'Getting {'all' if not max_commits else max_commits} commits for {owner}/{repo_name}')
        commits = client.get_repository_commits(owner, repo_name, max_results=max_commits)
        display_commits(commits)

        # get repository contents for the first repository
        logger.info(f'Getting repository contents')
        contents = client.get_repository_contents(owner, repo_name)
        display_contents(contents)

        # save results to github_api_results.json
        results = {
            'repositories': repos,
            'sample_commits': commits,
            'contents': contents
        }

        with open('github_api_results.json', 'w') as f:
            json.dump(results, f, indent=2)

        logger.info('Results saved to github_api_results.json')

    except requests.exceptions.RequestException as e:
        logger.exception(f'Network error: {e}')
    except Exception as e:
        logger.exception(f'Unexpected error: {e}')


def display_repos(repos):
    """Display repositories retrieved."""
    all_repo_data = []
    for repo in repos:
        if 'items' in repo:  # check if 'items' key exists
            # get relevant fields from the first 5 repositories
            repo_data = [
                {
                    'Repository': item['full_name'],
                    'Stars': item['stargazers_count'],
                    'Description': item['description']
                }
                for item in repo['items']
            ]
            all_repo_data.extend(repo_data)
        else:
            logger.error('No repositories found')
            sys.exit(1)
    df = pd.DataFrame(all_repo_data)
    with pd.option_context('display.max_rows', None, 'display.max_columns', None, 'display.max_colwidth', 30):
        logger.info('Sample repositories found:\n' + str(df.head()))


def display_commits(commits):
    """Display a sample of commits."""
    if not commits:
        logger.error('No commits found')
        return
    # get relevant fields
    commit_data = [
        {
            'SHA': commit['sha'],
            'Author': commit['commit']['author']['name'],
            'Message': commit['commit']['message'][:50],  # show the first 50 characters of the message
            'Date': commit['commit']['author']['date'],
            'URL': commit['commit']['url']
        }
        for commit in commits
    ]

    df = pd.DataFrame(commit_data)
    with pd.option_context('display.max_rows', None, 'display.max_columns', None, 'display.max_colwidth', 30):
        logger.info('Sample commits found:\n' + str(df.head()))


def display_contents(contents):
    """Display a sample of repository contents."""
    if not contents:
        logger.error('No repository contents found')
        return
    # get relevant fields
    contents_data = [
        {
            'Name': item['name'],
            'Type': item['type'],
            'Size': item['size'],
            'Path': item['path']
        }
        for item in contents
    ]

    df = pd.DataFrame(contents_data)
    with pd.option_context('display.max_rows', None, 'display.max_columns', None, 'display.max_colwidth', 30):
        logger.info('Sample contents found:\n' + str(df.head()))


if __name__ == '__main__':
    main()
