# KX Problem solving exercise

## Problem
We would like you to implement a distributed **Service Assembly** with a gateway component.

## Description
The service assembly will have the following components:
1) **Storage Service** - stores in-memory, dummy data that can be accessed through a REST GET call in JSON format
2) **Gateway Service** - main process that serves data to clients and tracks the availability of the Storage Services (there could be 0 to 3 available) and has the following REST endpoints
    * **/status** - returns the status of each Storage Service
    * **/data** - fetches the dummy data from a Storage Service (eg. with round robin) and returns the data in JSON format

We would like the services to be containerised and run with docker-compose.
The services can be implemented using any programming language.

## Architecture
<img src="https://user-images.githubusercontent.com/90027208/152865747-5c4734dd-c046-4170-ae04-f0ea1448cf89.png" width="300">

## Acceptance criteria
* Please fork this git repository and work inside your own
* Provide a solution for the described problem and give us the instructions necessary to execute it
* We would like to have your solution in form of a Pull Request into the main repository
* _What should the Gateway do if no Storage Services are running?_

## Run instructions
1. Start all services in background:
```bash
docker compose up -d --build
```

2. Open the Gateway Swagger UI:
`http://127.0.0.1:8080/docs`

3. Call `GET /status` and verify all storage services are up. Example response:
```json
{
  "services": [
    {"url": "http://172.31.0.11:8000", "status": "up"},
    {"url": "http://172.31.0.12:8000", "status": "up"},
    {"url": "http://172.31.0.13:8000", "status": "up"}
  ]
}
```

4. Call `GET /data` a few times. You should see round-robin behavior in `instance`:
```json
{
  "instance": "storage-1",
  "data": [
    {"id": 1, "name": "item-1", "value": "alpha"},
    {"id": 2, "name": "item-2", "value": "beta"},
    {"id": 3, "name": "item-3", "value": "gamma"}
  ]
}
```

5. Simulate one storage failure:
```bash
docker compose kill storage-2
```

6. Wait a few seconds (health check interval is 3s in the sample `.env`, configurable via `HEALTH_CHECK_INTERVAL` in `services/gateway/.env.gateway`), then call `GET /status` again. `storage-2` should become `down`.

7. Call `GET /data` again. The round robin should continue only across healthy services (`storage-1` and `storage-3`), skipping `storage-2`.

8. Start the killed storage again:
```bash
docker compose up -d storage-2
```

9. Re-check `GET /status` and confirm `storage-2` is `up` again.

10. Call `GET /data` a few times and confirm round robin includes `storage-2` again.

11. Simulate full outage by killing all storage services:
```bash
docker compose kill storage-1 storage-2 storage-3
```

12. Wait a few seconds (same configurable health-check interval), then call `GET /data` and confirm you get `503`. Note: unhealthy services are also removed reactively from the cached healthy list when a request to them fails (backoff behavior), not only by periodic health checks.
```json
{"detail": "No storage services available"}
```

13. Stop everything when done:
```bash
docker compose down
```
