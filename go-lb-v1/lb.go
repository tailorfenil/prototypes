package main

import (
    "fmt"
    "io"
    "log"
    "net"
    "time"
)

type Backend struct {
    Host string
    Port int
}

func (b *Backend) Addr() string {
    return fmt.Sprintf("%s:%d", b.Host, b.Port)
}

type IncomingReq struct {
    srcConn net.Conn
    reqId   string
}

type LB struct {
    listenAddr string
    backends   []*Backend
    strategy   Strategy
}

func NewLB(listenAddr string, backends []*Backend, strategy Strategy) *LB {
    return &LB{listenAddr: listenAddr, backends: backends, strategy: strategy}
}

func (lb *LB) Run() error {
    ln, err := net.Listen("tcp", lb.listenAddr)
    if err != nil {
        return fmt.Errorf("lb listen error: %w", err)
    }
    defer ln.Close()

    log.Printf("[lb] listening on %s", lb.listenAddr)

    for {
        conn, err := ln.Accept()
        if err != nil {
            log.Printf("[lb] accept error: %v", err)
            continue
        }

        go lb.proxy(IncomingReq{
            srcConn: conn,
            reqId:   newReqID(),
        })
    }
}

func (lb *LB) proxy(req IncomingReq) {
    defer req.srcConn.Close()

    backend := lb.strategy.GetNextBackend(req)
    if backend == nil {
        _, _ = req.srcConn.Write([]byte("no backend\n"))
        return
    }

    log.Printf("[lb] req=%s -> %s", req.reqId, backend.Addr())

    backendConn, err := net.DialTimeout("tcp", backend.Addr(), 800*time.Millisecond)
    if err != nil {
        _, _ = req.srcConn.Write([]byte("backend not available\n"))
        return
    }
    defer backendConn.Close()

    done := make(chan struct{}, 2)

    go func() {
        _, _ = io.Copy(backendConn, req.srcConn)
        done <- struct{}{}
    }()

    go func() {
        _, _ = io.Copy(req.srcConn, backendConn)
        done <- struct{}{}
    }()

    <-done
}
