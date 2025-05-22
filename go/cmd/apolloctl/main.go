package main

import (
    "fmt"

	"apollo-v2/go/cmd/apolloctl/ollama_checkhealth"
)

func main() {
    fmt.Println("Checking Ollama health...")
    ollama_checkhealth.CheckHealth()
}
