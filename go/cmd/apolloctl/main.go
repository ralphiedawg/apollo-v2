package main

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"
	"apollo-v2/internal/health"
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

func main() {
	rootCmd.AddCommand(healthCmd)
	rootCmd.AddCommand(versionCmd)
	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}
