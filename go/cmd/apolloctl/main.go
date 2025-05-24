package main

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
	"apollo-v2/internal/health"
	"apollo-v2/internal/canvas"
)

var rootCmd = &cobra.Command{
	Use:   "apolloctl",
	Short: "Apollo Control CLI",
	Long:  "A command-line tool for managing Apollo V2 services.",
}

var healthCmd = &cobra.Command{
	Use:   "check_health",
	Short: "Check Ollama health",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println("Checking Ollama health...")
		health.CheckOllamaHealth()
	},
}

var versionCmd = &cobra.Command{
	Use:   "version",
	Short: "Print the version number of Apollo V2",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Println("Apollo V2 CLI v0.1.0")
	},
}
var canvasSyncCmd = &cobra.Command{
	Use: 	"canvas_sync",
	Short: 	"Sync with canvas for the latest assignments",
	Run: 	func(cmd *cobra.Command, args []string) {
		canvas.FetchAssignments()
	},

}

func main() {
	rootCmd.AddCommand(healthCmd)
	rootCmd.AddCommand(versionCmd)
	rootCmd.AddCommand(canvasSyncCmd)
	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}
