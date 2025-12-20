package main

import "sync/atomic"

type Strategy interface {
    GetNextBackend(req IncomingReq) *Backend
}

type RoundRobinStrategy struct {
    backends []*Backend
    idx      uint64
}

func NewRoundRobinStrategy(backends []*Backend) *RoundRobinStrategy {
    return &RoundRobinStrategy{backends: backends}
}

func (s *RoundRobinStrategy) GetNextBackend(_ IncomingReq) *Backend {
    n := uint64(len(s.backends))
    if n == 0 {
        return nil
    }
    i := atomic.AddUint64(&s.idx, 1)
    return s.backends[i%n]
}
