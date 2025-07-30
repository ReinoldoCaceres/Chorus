package config

import (
	"os"
	"strconv"
	"time"
)

type Config struct {
	Port         string
	RedisURL     string
	RedisDB      int
	PresenceTTL  time.Duration
}

func LoadConfig() *Config {
	presenceTTL, _ := strconv.Atoi(getEnv("PRESENCE_TTL_SECONDS", "120"))
	redisDB, _ := strconv.Atoi(getEnv("REDIS_DB", "0"))
	
	return &Config{
		Port:        getEnv("PORT", "8081"),
		RedisURL:    getEnv("REDIS_URL", "redis://localhost:6379"),
		RedisDB:     redisDB,
		PresenceTTL: time.Duration(presenceTTL) * time.Second,
	}
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}