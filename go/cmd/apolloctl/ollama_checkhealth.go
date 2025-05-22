package main	

import (
	"fmt"
	"os"
	"net/http"
)

func main() {
	response, err := http.Get("http://localhost:11434/api/tags")

	if err != nil {
		fmt.Print(err.Error())
		fmt.Print("Ollama healthcheck failed. Exiting...")
		os.Exit(1)
	}
	if response.StatusCode == 200 {
		fmt.Print("Ollama system online")
	}
	os.Exit(0)
}
