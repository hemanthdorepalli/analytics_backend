from locust import HttpUser, task, between
import random
import json


class AnalyticsPlatformUser(HttpUser):
    wait_time = between(0.5, 2)
    token = None
    org_id = None

    def on_start(self):
        """Login before running tasks."""
        response = self.client.post("/api/v1/auth/login/", json={
            "email": "loadtest@example.com",
            "password": "LoadTest123!",
        })
        if response.status_code == 200:
            # Extract org_id from profile
            profile = self.client.get("/api/v1/auth/profile/")
            # Set org header for subsequent requests
            self.org_id = "your-org-id-here"

    @task(5)
    def ingest_single_event(self):
        """High frequency — event ingestion."""
        self.client.post(
            "/api/v1/ingestion/events/",
            json={
                "event_type": "page_view",
                "event_name": random.choice(["homepage", "dashboard", "settings", "login"]),
                "properties": {
                    "url": f"/page/{random.randint(1, 100)}",
                    "duration_ms": random.randint(100, 5000),
                },
                "user_id": f"user_{random.randint(1, 1000)}",
            },
            headers={"X-Organization-ID": self.org_id or ""},
        )

    @task(3)
    def ingest_batch_events(self):
        """Batch ingestion."""
        events = [
            {
                "event_type": "click",
                "event_name": f"button_{i}",
                "properties": {"label": f"btn_{i}"},
            }
            for i in range(random.randint(5, 20))
        ]
        self.client.post(
            "/api/v1/ingestion/events/batch/",
            json={"events": events},
            headers={"X-Organization-ID": self.org_id or ""},
        )

    @task(2)
    def list_dashboards(self):
        self.client.get(
            "/api/v1/dashboards/",
            headers={"X-Organization-ID": self.org_id or ""},
        )

    @task(1)
    def list_alert_rules(self):
        self.client.get(
            "/api/v1/alerts/rules/",
            headers={"X-Organization-ID": self.org_id or ""},
        )

    @task(1)
    def health_check(self):
        self.client.get("/health/")
