# Go Load Balancer – Version 1

This is a **minimal TCP load balancer** implemented in Go.

## What this version does
- TCP backend workers (simulated servers)
- TCP load balancer
- Round-robin backend selection
- Bidirectional proxy using io.Copy

## How to run

### 1. Start backend workers (in separate terminals)
```bash
go run worker.go --port 8081
go run worker.go --port 8082
go run worker.go --port 8083
```

### 2. Start the load balancer
```bash
go run .
```

### 3. Test
```bash
nc localhost 9090
```

You should see responses from different workers on each connection.
