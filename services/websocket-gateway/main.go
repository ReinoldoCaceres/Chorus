package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"chorus/websocket-gateway/config"
	"chorus/websocket-gateway/handlers"
	"chorus/websocket-gateway/middleware"
)

func main() {
	// Load configuration
	cfg := config.LoadConfig()
	
	// Setup logger
	logger := log.New(os.Stdout, "[WebSocket-Gateway] ", log.LstdFlags|log.Lshortfile)
	
	// Create HTTP mux
	mux := http.NewServeMux()
	
	// Health check endpoint
	mux.HandleFunc("/health", handlers.HealthCheck)
	
	// WebSocket endpoint with JWT authentication
	mux.Handle("/ws", middleware.JWTAuth(cfg.JWTSecret, http.HandlerFunc(handlers.WebSocketHandler)))
	
	// Create HTTP server
	srv := &http.Server{
		Addr:         ":" + cfg.Port,
		Handler:      middleware.Logging(logger, mux),
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}
	
	// Start server in goroutine
	go func() {
		logger.Printf("Starting WebSocket Gateway on port %s", cfg.Port)
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