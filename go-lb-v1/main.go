package main

import (
	"flag"
	"log"
	"net"
	"time"
)

// func main() {
//     backends := []*Backend{
//         {Host: "localhost", Port: 8081},
//         {Host: "localhost", Port: 8082},
//         {Host: "localhost", Port: 8083},
//     }

//     lb := NewLB(":9090", backends, NewRoundRobinStrategy(backends))
//     log.Fatal(lb.Run())
// }

func main() {
        listen := flag.String("listen", ":9090", "LB listen address (VIP)")
        name := flag.String("name", "lb", "instance name for logs")
        flag.Parse()
    
        backends := []*Backend{
            {Host: "localhost", Port: 8081},
            {Host: "localhost", Port: 8082},
            {Host: "localhost", Port: 8083},
        }
    
        lb := NewLB(*listen, backends, NewRoundRobinStrategy(backends))
    
        for {
            ln, err := net.Listen("tcp", *listen)
            if err != nil {
                // Another LB already owns the VIP port -> we are standby.
                log.Printf("[%s] STANDBY: cannot bind %s (%v). Retrying...", *name, *listen, err)
                time.Sleep(800 * time.Millisecond)
                continue
            }
    
            // We successfully bound VIP -> we are leader/active.
            log.Printf("[%s] ACTIVE: acquired VIP %s", *name, *listen)
    
            // Serve will block until accept fails (e.g., process gets killed, listener errors, etc.)
            err = lb.Serve(ln)
            log.Printf("[%s] lost VIP (Serve ended: %v). Going back to standby loop...", *name, err)
    
            time.Sleep(500 * time.Millisecond)
        }
}

