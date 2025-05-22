package health

import (
	"fmt"
	"net/http"
	"os"
)

// CheckOllamaHealth verifies if the Ollama service is running
func CheckOllamaHealth() {
	response, err := http.Get("http://localhost:11434/api/tags")
	if err != nil {
		fmt.Println(err.Error())
		fmt.Println("Ollama healthcheck failed. Exiting...")
		os.Exit(1)
	}
	defer response.Body.Close() // Properly close the response body
	
	if response.StatusCode == 200 {
		fmt.Println("Ollama system online")
	} else {
		fmt.Printf("Ollama returned unexpected status code: %d\n", response.StatusCode)
		os.Exit(1)
	}
}
