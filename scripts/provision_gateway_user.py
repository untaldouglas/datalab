#!/usr/bin/env python3
"""Provision the non-administrative Dremio identity used by metrics-gateway."""
import os

import requests


def main():
    host = os.environ["DREMIO_HOST"].rstrip("/")
    session = requests.Session()
    response = session.post(
        f"{host}/apiv2/login",
        json={"userName": os.environ["DREMIO_USERNAME"], "password": os.environ["DREMIO_PASSWORD"]},
        timeout=15,
    )
    response.raise_for_status()
    session.headers["Authorization"] = f"Bearer {response.json()['token']}"
    lookup = session.get(f"{host}/api/v3/user/by-name/metrics_gateway", timeout=15)
    if lookup.status_code == 200:
        print("metrics_gateway ya existe.")
        return
    if lookup.status_code != 404:
        lookup.raise_for_status()
    response = session.post(
        f"{host}/api/v3/user",
        json={"name": "metrics_gateway", "firstName": "Metrics", "lastName": "Gateway", "email": "metrics-gateway@poc.local", "password": os.environ["DREMIO_GATEWAY_PASSWORD"]},
        timeout=15,
    )
    response.raise_for_status()
    print("metrics_gateway creado sin privilegios administrativos.")


if __name__ == "__main__":
    main()
