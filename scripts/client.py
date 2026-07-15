import os
import time
import requests
from dotenv import load_dotenv
from scripts.logger import setup_logger

logger = setup_logger()

# Load local environment variables if .env file is present
load_dotenv()

class GitHubAPIError(Exception):
    """Exception class for GitHub API related errors."""
    pass

class GitHubGraphQLClient:
    """
    Interface for querying the GitHub GraphQL API with robust error handling,
    exponential backoff retries, rate-limit awareness, and dynamic token detection.
    """
    GRAPHQL_URL = "https://api.github.com/graphql"

    def __init__(self, token=None, mock_mode=False):
        self.mock_mode = mock_mode
        self.token = token or os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
        
        if not self.token and not self.mock_mode:
            logger.warning("No GitHub Token detected (checked GH_TOKEN and GITHUB_TOKEN). Attempting offline cache.")
            self.mock_mode = True

        self.headers = {
            "Authorization": f"bearer {self.token}",
            "User-Agent": "github-skyline-hub-client"
        } if self.token else {}

    def execute_query(self, query, variables=None, retries=3, backoff_factor=2):
        """
        Executes a GraphQL query with retries, exponential backoff, and error parsing.
        """
        if self.mock_mode:
            logger.info("GraphQL client running in mock mode. Queries will return offline mock data.")
            return self._get_mock_response(query, variables)

        for attempt in range(1, retries + 1):
            try:
                response = requests.post(
                    self.GRAPHQL_URL,
                    json={"query": query, "variables": variables},
                    headers=self.headers,
                    timeout=15
                )
                
                # Check HTTP Rate Limit Headers or 403 Forbidden
                if response.status_code == 403 or response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(f"Rate limited (status {response.status_code}). Retrying after {retry_after}s.")
                    time.sleep(retry_after)
                    continue

                if response.status_code >= 500:
                    # Server errors are retried
                    sleep_time = backoff_factor ** attempt
                    logger.warning(f"GitHub Server Error ({response.status_code}). Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)
                    continue

                response.raise_for_status()
                data = response.json()

                if "errors" in data:
                    errors = data["errors"]
                    error_msg = "; ".join([e.get("message", "Unknown error") for e in errors])
                    # Check if error is related to authentication
                    if any("type" in e and e["type"] == "NOT_FOUND" for e in errors):
                        raise GitHubAPIError(f"Resource not found: {error_msg}")
                    raise GitHubAPIError(f"GitHub GraphQL query error: {error_msg}")

                return data.get("data", {})

            except requests.RequestException as e:
                sleep_time = backoff_factor ** attempt
                logger.warning(f"Network error (attempt {attempt}/{retries}): {e}. Retrying in {sleep_time}s...")
                time.sleep(sleep_time)

        raise GitHubAPIError("Max retries exceeded while querying GitHub GraphQL API.")

    def get_user_metadata(self, username):
        """
        Fetches registration date (createdAt) and repository count for a user.
        """
        query = """
        query($login: String!) {
          user(login: $login) {
            createdAt
            repositories {
              totalCount
            }
          }
        }
        """
        variables = {"login": username}
        data = self.execute_query(query, variables)
        
        if not data or "user" not in data or not data["user"]:
            raise GitHubAPIError(f"Failed to fetch metadata. User '{username}' may not exist.")
            
        user_info = data["user"]
        return {
            "created_at": user_info["createdAt"],
            "repo_count": user_info["repositories"]["totalCount"]
        }

    def get_contribution_calendar(self, username, start_date_iso, end_date_iso):
        """
        Fetches the contribution calendar for a single user between start and end ISO timestamps.
        """
        query = """
        query($login: String!, $from: DateTime, $to: DateTime) {
          user(login: $login) {
            contributionsCollection(from: $from, to: $to) {
              contributionCalendar {
                totalContributions
                weeks {
                  contributionDays {
                    contributionCount
                    date
                    color
                    contributionLevel
                    weekday
                  }
                }
              }
            }
          }
        }
        """
        variables = {
            "login": username,
            "from": start_date_iso,
            "to": end_date_iso
        }
        data = self.execute_query(query, variables)
        
        try:
            collection = data["user"]["contributionsCollection"]
            return collection["contributionCalendar"]
        except (KeyError, TypeError) as e:
            raise GitHubAPIError(f"Failed to parse contribution calendar response: {e}")

    def _get_mock_response(self, query, variables):
        """
        Returns hardcoded realistic Mock responses for testing and offline development.
        """
        username = variables.get("login") if variables else "Durgesh729"
        
        # Determine if it's metadata or calendar query
        if "createdAt" in query:
            return {
                "user": {
                    "createdAt": "2020-05-15T08:30:00Z",
                    "repositories": {
                        "totalCount": 24
                    }
                }
            }
        else:
            # Calendar query
            from_date = variables.get("from")[:4] if variables else "2025"
            logger.info(f"Generating mock contribution calendar data for {username} in year {from_date}")
            
            # Construct a basic 53-week layout
            mock_weeks = []
            import datetime
            year = int(from_date)
            current_date = datetime.date(year, 1, 1)
            
            # Align to sunday of the first week
            start_weekday = (current_date.weekday() + 1) % 7 # 0 = Sunday
            current_date -= datetime.timedelta(days=start_weekday)
            
            total_contributions = 0
            year_seed = year % 10
            for w in range(53):
                days = []
                for d in range(7):
                    day_idx = w * 7 + d
                    is_active = (day_idx % (3 + (year_seed % 3)) != 0) or (200 - (year_seed * 10) < day_idx < 250 + (year_seed * 5))
                    count = 0
                    if is_active:
                        weight = (26.5 - abs(26.5 - w)) / 26.5
                        count = int(((day_idx + year_seed) % 8 + 1) * (weight * 4) + 1)
                    
                    total_contributions += count
                    
                    level = "NONE"
                    color = "#ebedf0"
                    if count > 0:
                        if count < 3:
                            level = "FIRST_QUARTILE"
                            color = "#9be9a8"
                        elif count < 6:
                            level = "SECOND_QUARTILE"
                            color = "#40c463"
                        elif count < 9:
                            level = "THIRD_QUARTILE"
                            color = "#30a14e"
                        else:
                            level = "FOURTH_QUARTILE"
                            color = "#216e39"
                            
                    days.append({
                        "contributionCount": count,
                        "date": current_date.isoformat(),
                        "color": color,
                        "contributionLevel": level,
                        "weekday": d
                    })
                    current_date += datetime.timedelta(days=1)
                mock_weeks.append({"contributionDays": days})
                
            return {
                "user": {
                    "contributionsCollection": {
                        "contributionCalendar": {
                            "totalContributions": total_contributions,
                            "weeks": mock_weeks
                        }
                    }
                }
            }
