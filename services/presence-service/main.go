package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"chorus/presence-service/config"
	"chorus/presence-service/handlers"
	"chorus/presence-service/services"
)

func main() {
	// Load configuration
	cfg := config.LoadConfig()
	
	// Setup logger
	logger := log.New(os.Stdout, "[Presence-Service] ", log.LstdFlags|log.Lshortfile)
	
	// Initialize Redis client
	redisClient := services.NewRedisClient(cfg)
	defer redisClient.Close()
	
	// Initialize presence service
	presenceService := services.NewPresenceService(redisClient, logger)
	
	// Create handlers
	presenceHandler := handlers.NewPresenceHandler(presenceService, logger)
	
	// Setup routes
	mux := http.NewServeMux()
	mux.HandleFunc("/health", handlers.HealthCheck)
	mux.HandleFunc("/presence/heartbeat", presenceHandler.Heartbeat)
	mux.HandleFunc("/presence/status", presenceHandler.GetStatus)
	mux.HandleFunc("/presence/online", presenceHandler.GetOnlineUsers)
	
	// Create HTTP server
	srv := &http.Server{
		Addr:         ":" + cfg.Port,
		Handler:      handlers.LoggingMiddleware(logger, mux),
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}
	
	// Start server in goroutine
	go func() {
		logger.Printf("Starting Presence Service on port %s", cfg.Port)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Fatalf("Failed to start server: %v", err)
		}
	}()
	
	// Wait for interrupt signal to gracefully shutdown the server
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	
	logger.Println("Shutting down server...")
	
	// Graceful shutdown with timeout
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	
	if err := srv.Shutdown(ctx); err != nil {
		logger.Fatalf("Server forced to shutdown: %v", err)
	}
	
	logger.Println("Server exited")
}