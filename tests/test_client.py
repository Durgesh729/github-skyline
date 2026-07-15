import pytest
from scripts.config import ConfigManager, ConfigError
from scripts.client import GitHubGraphQLClient, GitHubAPIError

def test_config_manager_load_and_validate(tmp_path):
    # Create a temporary config file
    config_file = tmp_path / "config.json"
    config_content = """{
      "username": "TestUser",
      "theme": "cyberpunk",
      "output_dir": "assets",
      "docs_dir": "docs",
      "github_pages_url": "https://TestUser.github.io/github-skyline/",
      "svg_settings": {},
      "animation_settings": {}
    }"""
    config_file.write_text(config_content)
    
    # Instantiate config manager
    cfg = ConfigManager(config_path=str(config_file))
    assert cfg.username == "TestUser"
    assert cfg.get("theme") == "cyberpunk"
    assert "name" in cfg.theme_data
    assert cfg.theme_data["name"] == "Cyberpunk"

def test_config_manager_missing_fields(tmp_path):
    config_file = tmp_path / "config_err.json"
    config_content = """{
      "username": "",
      "theme": "cyberpunk"
    }"""
    config_file.write_text(config_content)
    
    with pytest.raises(ConfigError):
        ConfigManager(config_path=str(config_file))

def test_graphql_client_mock_mode():
    client = GitHubGraphQLClient(mock_mode=True)
    meta = client.get_user_metadata("Durgesh729")
    assert "created_at" in meta
    assert meta["repo_count"] == 24
    
    calendar = client.get_contribution_calendar("Durgesh729", "2025-01-01T00:00:00Z", "2025-12-31T23:59:59Z")
    assert calendar["totalContributions"] > 0
    assert len(calendar["weeks"]) == 53
    assert len(calendar["weeks"][0]["contributionDays"]) == 7

def test_graphql_client_error_handling(monkeypatch):
    client = GitHubGraphQLClient(token="invalid_token")
    
    # Mock post call to return failure
    class MockResponse:
        status_code = 401
        def raise_for_status(self):
            raise requests.exceptions.HTTPError("401 Unauthorized")
            
    import requests
    monkeypatch.setattr(requests, "post", lambda *args, **kwargs: MockResponse())
    
    with pytest.raises(GitHubAPIError):
        client.get_user_metadata("Durgesh729")
