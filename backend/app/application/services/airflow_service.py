from typing import Optional, Dict, Any, List
import httpx
import json
from datetime import datetime, timezone
import base64

from app.core.config import settings
from app.core.retry import with_retry, EXTERNAL_SERVICE_RETRY, airflow_circuit_breaker
from app.shared.exceptions import ExternalServiceError


class AirflowClient:
    def __init__(self):
        self.base_url = settings.AIRFLOW_URL.rstrip("/")
        self.username = settings.AIRFLOW_USERNAME
        self.password = settings.AIRFLOW_PASSWORD
        self._auth_header = self._create_auth_header()

    def _create_auth_header(self) -> str:
        credentials = f"{self.username}:{self.password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded_credentials}"

    @with_retry(EXTERNAL_SERVICE_RETRY)
    @airflow_circuit_breaker
    async def _make_request(
        self, method: str, endpoint: str, **kwargs
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1{endpoint}"
        headers = {
            "Authorization": self._auth_header,
            "Content-Type": "application/json",
            **kwargs.pop("headers", {}),
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method=method, url=url, headers=headers, **kwargs
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise ExternalServiceError(f"Airflow API error: {str(e)}")
            except json.JSONDecodeError:
                raise ExternalServiceError("Invalid JSON response from Airflow")

    async def trigger_dag(
        self,
        dag_id: str,
        dag_run_id: Optional[str] = None,
        conf: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload = {
            "dag_run_id": dag_run_id
            or f"api_trigger_{datetime.now(timezone.utc).isoformat()}",
            "conf": conf or {},
        }

        return await self._make_request("POST", f"/dags/{dag_id}/dagRuns", json=payload)

    async def get_dag_run_status(self, dag_id: str, dag_run_id: str) -> Dict[str, Any]:
        return await self._make_request("GET", f"/dags/{dag_id}/dagRuns/{dag_run_id}")

    async def get_dag_runs(
        self,
        dag_id: str,
        limit: int = 100,
        offset: int = 0,
        state: Optional[str] = None,
    ) -> Dict[str, Any]:
        params = {"limit": limit, "offset": offset}
        if state:
            params["state"] = state

        return await self._make_request("GET", f"/dags/{dag_id}/dagRuns", params=params)

    async def patch_dag_run(
        self, dag_id: str, dag_run_id: str, state: str
    ) -> Dict[str, Any]:
        payload = {"state": state}

        return await self._make_request(
            "PATCH", f"/dags/{dag_id}/dagRuns/{dag_run_id}", json=payload
        )

    async def clear_dag_run(self, dag_id: str, dag_run_id: str) -> Dict[str, Any]:
        payload = {
            "dry_run": False,
            "dag_run_id": dag_run_id,
            "reset_dag_runs": True,
            "task_ids": [],
        }

        return await self._make_request(
            "POST", f"/dags/{dag_id}/clearTaskInstances", json=payload
        )

    async def get_task_instances(self, dag_id: str, dag_run_id: str) -> Dict[str, Any]:
        return await self._make_request(
            "GET", f"/dags/{dag_id}/dagRuns/{dag_run_id}/taskInstances"
        )

    async def get_dag_details(self, dag_id: str) -> Dict[str, Any]:
        return await self._make_request("GET", f"/dags/{dag_id}")

    async def list_dags(
        self, limit: int = 100, offset: int = 0, only_active: bool = True
    ) -> Dict[str, Any]:
        params = {"limit": limit, "offset": offset, "only_active": only_active}

        return await self._make_request("GET", "/dags", params=params)
