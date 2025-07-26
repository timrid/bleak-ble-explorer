import requests


class EmulatorControllerClient:
    def __init__(self):
        self.base_url = "http://localhost:8000/"

    def ping(self):
        response = self.get("ping")
        if response != "pong":
            raise RuntimeError(f"Unexpected response: {response}")

    def grand_permission(self, package: str, permission: str):
        self.post(
            "grant_permission",
            params={
                "package": package,
                "permission": permission,
            },
        )

    def revoke_permission(self, package: str, permission: str):
        self.post(
            "revoke_permission",
            params={
                "package": package,
                "permission": permission,
            },
        )

    def activate_bluetooth(self):
        self.post("activate_bluetooth")

    def gatt_server_start(self):
        self.post("gatt_server/start")

    def get(self, path: str, **kwargs):
        url = f"{self.base_url}{path}"
        response = requests.get(url, **kwargs)
        response.raise_for_status()
        return response.json()

    def post(self, path: str, data=None, json=None, **kwargs):
        url = f"{self.base_url}{path}"
        response = requests.post(url, data=data, json=json, **kwargs)
        if response.status_code == 500:
            raise RuntimeError(f"Server error: {response.text}")
        response.raise_for_status()
        return response.json()
