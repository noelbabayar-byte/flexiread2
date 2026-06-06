"""Basic Locust load-test skeleton for FlexiRead API."""

from locust import HttpUser, between, task


class FlexiReadApiUser(HttpUser):
    wait_time = between(1, 5)

    @task
    def health_check(self):
        self.client.get("/health")
