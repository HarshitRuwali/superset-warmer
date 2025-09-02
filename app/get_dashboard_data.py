
import json
import requests

def get_token(config: dict):
    url = f"{config['url']}/api/v1/security/login"
    payload = {
        "username": config["user"],
        "password": config["password"],
        "provider": config["provider"],
        "refresh": True
    }
    resp = requests.post(url, json=payload)
    resp.raise_for_status()
    return resp.json()["access_token"]

def list_dashboards(config, token, page_size=1000):
    url = f"{config['url']}/api/v1/dashboard/"
    headers = {"Authorization": f"Bearer {token}"}
    page_size_params = {"page_size": page_size}
    params = {"q": json.dumps(page_size_params)}
    resp = requests.get(url, headers=headers, params=params)
    resp.raise_for_status()
    return resp.json()

def get_dashboard_ids(config: dict):
    token = get_token(config)
    dashboards = list_dashboards(config, token)
    dashboard_ids = []
    for dash in dashboards.get("result", []):
        print(f"ID={dash['id']:>4}  Title={dash['dashboard_title']!r}")
        dashboard_ids.append(dash['id'])

    return dashboard_ids
