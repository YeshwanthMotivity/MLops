import time
import requests
from app.config import CVAT_URL, CVAT_USERNAME, CVAT_PASSWORD


def _check_response(r, action):
    """Check response and raise clear error if failed."""
    if r.ok:
        return
    print(f"ERROR: {action}")
    print(f"  Status: {r.status_code}")
    try:
        print(f"  Response: {r.json()}")
    except Exception:
        print(f"  Response: {r.text}")
    r.raise_for_status()


class CvatClient:
    def __init__(self):
        if not CVAT_URL:
            raise ValueError("CVAT_URL is not set")
        if not CVAT_USERNAME or not CVAT_PASSWORD:
            raise ValueError("CVAT_USERNAME or CVAT_PASSWORD is not set")

        self.base = CVAT_URL.rstrip("/")
        self.token = self._login()

    def _login(self):
        try:
            headers = {}
            if "host.docker.internal" in self.base:
                headers["Host"] = "localhost"

            r = requests.post(
                f"{self.base}/api/auth/login",
                json={"username": CVAT_USERNAME, "password": CVAT_PASSWORD},
                headers=headers,
                timeout=30
            )
        except requests.ConnectionError:
            raise ConnectionError(f"Cannot connect to CVAT at {self.base}")
        except requests.Timeout:
            raise TimeoutError(f"CVAT login timed out at {self.base}")

        _check_response(r, "CVAT login failed - check credentials")
        print(f"Logged in to CVAT at {self.base}")
        return r.json()["key"]

    def _headers(self):
        headers = {"Authorization": f"Token {self.token}"}
        # If we are connecting to the host from inside docker, Traefik (in CVAT)
        # expects the 'Host: localhost' header to route to the cvat_server.
        if "host.docker.internal" in self.base:
            headers["Host"] = "localhost"
        return headers

    # ---------------- PROJECT ----------------

    def get_project(self, name):
        r = requests.get(f"{self.base}/api/projects", headers=self._headers(), timeout=30)
        _check_response(r, "Failed to list projects")

        for p in r.json()["results"]:
            if p["name"] == name:
                print(f"Found existing project: {name} (id={p['id']})")
                return p["id"]
        return None

    def create_project(self, name, labels):
        r = requests.post(
            f"{self.base}/api/projects",
            headers=self._headers(),
            json={
                "name": name,
                "labels": [{"name": l} for l in labels]
            },
            timeout=30
        )
        _check_response(r, f"Failed to create project '{name}'")
        project_id = r.json()["id"]
        print(f"Created project: {name} (id={project_id})")
        return project_id

    def ensure_project(self, name, labels):
        project_id = self.get_project(name)
        if project_id:
            return project_id
        return self.create_project(name, labels)

    # ---------------- TASK ----------------

    def create_task(self, project_id, name):
        r = requests.post(
            f"{self.base}/api/tasks",
            headers=self._headers(),
            json={"name": name, "project_id": project_id},
            timeout=30
        )
        _check_response(r, f"Failed to create task '{name}' in project {project_id}")
        task_id = r.json()["id"]
        print(f"Created task: {name} (id={task_id})")
        return task_id

    def attach_images(self, task_id, paths):
        print(f"Attaching {len(paths)} images to task {task_id}...")
        r = requests.post(
            f"{self.base}/api/tasks/{task_id}/data",
            headers=self._headers(),
            json={"server_files": paths, "image_quality": 70},
            timeout=120
        )
        _check_response(r, f"Failed to attach images to task {task_id}")
        print(f"Attached {len(paths)} images to task {task_id}")

    # ---------------- EXPORT ----------------

    def get_task_status(self, task_id):
        """GET /api/tasks/{id} — returns task info."""
        r = requests.get(
            f"{self.base}/api/tasks/{task_id}",
            headers=self._headers(),
            timeout=30
        )
        _check_response(r, f"Failed to get task {task_id}")
        return r.json()

    def get_task_jobs(self, task_id):
        """GET /api/jobs?task_id={id} — returns individual job details."""
        r = requests.get(
            f"{self.base}/api/jobs",
            headers=self._headers(),
            params={"task_id": task_id},
            timeout=30
        )
        _check_response(r, f"Failed to get jobs for task {task_id}")
        return r.json().get("results", [])

    def export_annotations(self, task_id):
        """
        POST export request for COCO 1.0 annotations (no images).
        Returns the rq_id used to poll for completion.
        """
        r = requests.post(
            f"{self.base}/api/tasks/{task_id}/dataset/export",
            headers=self._headers(),
            params={"format": "COCO 1.0", "save_images": "false"},
            timeout=60
        )
        _check_response(r, f"Failed to request annotation export for task {task_id}")
        rq_id = r.json().get("rq_id")
        if not rq_id:
            raise RuntimeError(f"No rq_id returned from export request for task {task_id}")
        print(f"Export requested for task {task_id} (rq_id={rq_id})")
        return rq_id

    def download_export(self, rq_id, max_wait=300):
        """
        Poll GET /api/requests/{rq_id} until finished, then download ZIP bytes.
        Raises TimeoutError after max_wait seconds.
        """
        start = time.time()
        poll_interval = 2

        while True:
            elapsed = time.time() - start
            if elapsed > max_wait:
                raise TimeoutError(
                    f"CVAT export timed out after {max_wait}s (rq_id={rq_id})"
                )

            r = requests.get(
                f"{self.base}/api/requests/{rq_id}",
                headers=self._headers(),
                timeout=30
            )
            _check_response(r, f"Failed to poll export status (rq_id={rq_id})")
            data = r.json()
            status = data.get("status")

            if status == "finished":
                # download the result
                result_url = data.get("result_url")
                if not result_url:
                    raise RuntimeError(f"Export finished but no result_url (rq_id={rq_id})")

                # result_url may be absolute (pointing to localhost) or relative
                from urllib.parse import urlparse
                parsed_result = urlparse(result_url)
                
                # If absolute, extract path and query to reconstruct with self.base
                if parsed_result.scheme and parsed_result.netloc:
                    path_with_query = parsed_result.path
                    if parsed_result.query:
                        path_with_query += f"?{parsed_result.query}"
                    result_url = f"{self.base}{path_with_query}"
                elif result_url.startswith("/"):
                    result_url = f"{self.base}{result_url}"

                dr = requests.get(result_url, headers=self._headers(), timeout=120)
                _check_response(dr, "Failed to download export ZIP")
                print(f"Downloaded export ({len(dr.content)} bytes)")
                return dr.content

            if status == "failed":
                message = data.get("message", "unknown error")
                raise RuntimeError(f"CVAT export failed: {message} (rq_id={rq_id})")

            print(f"  Export status: {status} ({elapsed:.0f}s elapsed)")
            time.sleep(poll_interval)

