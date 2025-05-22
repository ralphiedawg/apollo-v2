# Apollo V2 Go Components

This directory contains Go code for the Apollo V2 project.

## Project Structure

- `cmd/apolloctl`: Main command-line application entry point
- `internal/health`: Internal health check utilities

## Build Instructions

To build the apolloctl command:

```bash
cd go
go build ./cmd/apolloctl
```

## Development

When adding new functionality:
1. Follow Go project layout conventions
2. Use Go modules for dependency management
3. Ensure proper error handling
