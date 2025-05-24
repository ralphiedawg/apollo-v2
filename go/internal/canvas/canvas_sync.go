package canvas

import (
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"github.com/joho/godotenv"
)

func FetchAssignments() error {
	fmt.Println("Fetching assignments from Canvas API...")
	godotenv.Load()
	key := os.Getenv("CANVAS_API_KEY")
	baseURL := os.Getenv("CANVAS_API_URL")
	if key == "" || baseURL == "" {
		return fmt.Errorf("missing CANVAS_API_KEY or CANVAS_API_URL environment variables")
	}

	req, err := http.NewRequest("GET", baseURL+"/api/v1/calendar_events", nil)
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}
	req.Header.Set("Authorization", "Bearer "+key)

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to perform request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("Canvas API error: %s\n%s", resp.Status, string(body))
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("failed to read response: %w", err)
	}

	// Prepare the output path
	cachePath := filepath.Clean("../../../../cache/canvas_sync.json")
	if err := os.MkdirAll(filepath.Dir(cachePath), 0755); err != nil {
		return fmt.Errorf("failed to create cache directory: %w", err)
	}

	f, err := os.Create(cachePath)
	if err != nil {
		return fmt.Errorf("failed to open cache file: %w", err)
	}
	defer f.Close()

	if _, err := f.Write(body); err != nil {
		return fmt.Errorf("failed to write to cache file: %w", err)
	}

	fmt.Println("Assignments cached at", cachePath)
	return nil
}
