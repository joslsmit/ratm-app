import requests
import os
from datetime import datetime

def download_file(url, local_filename):
    """Downloads a file from a URL to a local path, checking for updates."""
    try:
        # Check if file exists and get its last modified time
        if os.path.exists(local_filename):
            local_mtime = datetime.fromtimestamp(os.path.getmtime(local_filename))
            
            # Get remote file's last modified time
            head_response = requests.head(url)
            head_response.raise_for_status()
            
            if 'Last-Modified' in head_response.headers:
                remote_mtime_str = head_response.headers['Last-Modified']
                remote_mtime = datetime.strptime(remote_mtime_str, '%a, %d %b %Y %H:%M:%S GMT')

                if local_mtime >= remote_mtime:
                    print(f"'{local_filename}' is up to date. Skipping download.")
                    return True
        
        # Download the file if it's new or updated
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(local_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"Successfully downloaded {local_filename}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {url}: {e}")
        return False

def import_data():
    """Imports all the required data from the DynastyProcess repository."""
    base_url = "https://raw.githubusercontent.com/dynastyprocess/data/master/files/"
    files_to_download = [
        "db_fpecr_latest.csv",
        "db_playerids.csv",
        "values-players.csv",
        "values-picks.csv",
        "fp_latest_weekly.csv" # Added for more recent data
    ]
    
    backend_dir = os.path.dirname(os.path.abspath(__file__))

    for filename in files_to_download:
        url = f"{base_url}{filename}"
        local_path = os.path.join(backend_dir, filename)
        download_file(url, local_path)

if __name__ == "__main__":
    import_data()
