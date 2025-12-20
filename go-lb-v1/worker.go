package main

import (
    "flag"
    "fmt"
    "log"
    "net"
)

func main() {
    port := flag.Int("port", 8081, "port to listen on")
    flag.Parse()

    ln, err := net.Listen("tcp", fmt.Sprintf(":%d", *port))
    if err != nil {
        log.Fatalf("worker listen error: %v", err)
    }
    log.Printf("[worker %d] listening", *port)

    for {
        conn, err := ln.Accept()
        if err != nil {
            log.Printf("[worker %d] accept error: %v", *port, err)
            continue
        }
        go func(c net.Conn) {
            defer c.Close()
            msg := fmt.Sprintf("hello from worker :%d\n", *port)
            _, _ = c.Write([]byte(msg))
        }(conn)
    }
}
