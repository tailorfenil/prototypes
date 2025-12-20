package main

import "log"

func main() {
    backends := []*Backend{
        {Host: "localhost", Port: 8081},
        {Host: "localhost", Port: 8082},
        {Host: "localhost", Port: 8083},
    }

    lb := NewLB(":9090", backends, NewRoundRobinStrategy(backends))
    log.Fatal(lb.Run())
}
