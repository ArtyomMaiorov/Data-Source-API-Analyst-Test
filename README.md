# Data-Source-API-Analyst-Test
Homework assignment for Data Source API Analyst role.

## Project Structure

- `/Content`: API documentation, Python code, and troubleshooting guides
  - `api_documentation.md`: Detailed documentation of the GitHub API endpoints used
  - `github_api_client.py`: Python implementation of the GitHub API client using requests
  - `troubleshooting_guide.md`: Guides for troubleshooting and data-cleaning approach
- `/Postman_Collection`: Contains the Google Colab notebook
  - `github_api_test.ipynb`: Notebook with API testing implementation
  
## Implementation

This solution uses GitHub API to search public repositories, get commits information and get repository contents

requests, pandas and logging libraries are used to interact with API. Key features are:
1. Rate limit handling
2. Error handling
3. Pagination support using links headers
4. Data extraction and cleaning
5. Results are stored in JSON
6. Logging system
7. Results display

## Reflection

Many points of the assignment seemed ambiguous and required extra time to understand what specific outcome is expected