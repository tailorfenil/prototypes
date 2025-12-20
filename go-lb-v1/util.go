package main

import (
    "crypto/rand"
    "encoding/hex"
)

func newReqID() string {
    var b [8]byte
    _, _ = rand.Read(b[:])
    return hex.EncodeToString(b[:])
}
