import requests
from core.logger import AppLogger

class Updater:
    """
    Updater — Check for software updates using the GitHub Releases API.
    """
    def __init__(self, current_version: str, repo_owner: str, repo_name: str):
        self._logger = AppLogger.instance()
        self._current_version = current_version
        self._repo_owner = repo_owner
        self._repo_name = repo_name

    def check_for_updates(self) -> dict:
        """
        Query the GitHub Releases API for the latest release.

        Returns:
            dict with keys:
              update_available : bool
              current_version  : str
              latest_version   : str
              download_url     : str   (first .exe asset, or "" if none)
              message          : str
        """
        api_url = f"https://api.github.com/repos/{self._repo_owner}/{self._repo_name}/releases/latest"
        
        try:
            resp = requests.get(
                api_url, 
                timeout=10, 
                headers={'Accept': 'application/vnd.github+json'}
            )
            
            if resp.status_code != 200:
                self._logger.info(f"GitHub update check returned HTTP {resp.status_code}")
                return {
                    "update_available": False,
                    "current_version": self._current_version,
                    "message": f"GitHub API returned {resp.status_code}"
                }
            
            release = resp.json()
            latest_tag = release.get("tag_name", "")
            
            if latest_tag != self._current_version:
                download_url = ""
                for asset in release.get("assets", []):
                    name = asset.get("name", "")
                    if name.lower().endswith(".exe"):
                        download_url = asset.get("browser_download_url", "")
                        break
                
                return {
                    "update_available": True,
                    "current_version": self._current_version,
                    "latest_version": latest_tag,
                    "download_url": download_url,
                    "message": f"New version available: {latest_tag}"
                }
            else:
                return {
                    "update_available": False,
                    "current_version": self._current_version,
                    "latest_version": latest_tag,
                    "message": "You are on the latest version"
                }
                
        except requests.exceptions.ConnectionError:
            self._logger.info("Update check skipped — no internet connection")
            return {
                "update_available": False,
                "current_version": self._current_version,
                "message": "No internet connection"
            }
        except Exception as e:
            self._logger.error(f"Update check failed: {str(e)}")
            return {
                "update_available": False,
                "current_version": self._current_version,
                "message": f"Error: {str(e)}"
            }
