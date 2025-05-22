package main

import (
	"fmt"
	"apollo-v2/internal/health"
)

func main() {
	fmt.Println("Checking Ollama health...")
	health.CheckOllamaHealth()
}
