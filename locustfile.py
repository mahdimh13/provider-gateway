from locust import HttpUser, task, between

class GatewayUser(HttpUser):
    wait_time = between(0.0, 0.05)
    @task
    def process(self):
        self.client.post('/v1/process', json={'payload': {'operation': 'benchmark', 'value': 42}}, name='/v1/process')
