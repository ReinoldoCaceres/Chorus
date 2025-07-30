package services

import (
	"context"
	"log"

	"github.com/redis/go-redis/v9"
	"chorus/presence-service/config"
)

func NewRedisClient(cfg *config.Config) *redis.Client {
	opt, err := redis.ParseURL(cfg.RedisURL)
	if err != nil {
		log.Fatalf("Failed to parse Redis URL: %v", err)
	}
	
	opt.DB = cfg.RedisDB
	
	client := redis.NewClient(opt)
	
	// Test connection
	ctx := context.Background()
	if err := client.Ping(ctx).Err(); err != nil {
		log.Fatalf("Failed to connect to Redis: %v", err)
	}
	
	log.Println("Connected to Redis successfully")
	return client
}