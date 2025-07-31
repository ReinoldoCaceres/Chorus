package config

import (
	"os"

	"github.com/joho/godotenv"
)

type Config struct {
	// Server configuration
	Port        string
	Environment string

	// Database configuration
	DatabaseURL string

	// Redis configuration
	RedisURL string

	// JWT configuration
	JWTSecret string

	// Workflow engine configuration
	MaxConcurrentWorkflows int
	WorkflowCheckInterval  int // in seconds
	StepRetryLimit         int
	StepTimeout            int // in seconds
}

func LoadConfig() *Config {
	// Load .env file if it exists
	_ = godotenv.Load()

	return &Config{
		Port:        getEnv("PORT", "8081"),
		Environment: getEnv("ENVIRONMENT", "development"),

		DatabaseURL: getEnv("DATABASE_URL", "postgres://chorus:password@localhost:5432/chorus?sslmode=disable"),
		RedisURL:    getEnv("REDIS_URL", "redis://localhost:6379"),

		JWTSecret: getEnv("JWT_SECRET", "your-secret-key"),

		MaxConcurrentWorkflows: getEnvAsInt("MAX_CONCURRENT_WORKFLOWS", 100),
		WorkflowCheckInterval:  getEnvAsInt("WORKFLOW_CHECK_INTERVAL", 10),
		StepRetryLimit:         getEnvAsInt("STEP_RETRY_LIMIT", 3),
		StepTimeout:            getEnvAsInt("STEP_TIMEOUT", 300),
	}
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getEnvAsInt(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		// Simple conversion, in production you might want more robust parsing
		switch value {
		case "10":
			return 10
		case "100":
			return 100
		case "300":
			return 300
		case "3":
			return 3
		default:
			return defaultValue
		}
	}
	return defaultValue
}