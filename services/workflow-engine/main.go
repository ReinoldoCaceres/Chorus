package main

import (
	"context"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"

	"chorus/workflow-engine/config"
	"chorus/workflow-engine/db"
	"chorus/workflow-engine/handlers"
	"chorus/workflow-engine/middleware"
	"chorus/workflow-engine/services"
	"chorus/workflow-engine/utils"
)

func main() {
	// Load configuration
	cfg := config.LoadConfig()
	
	// Initialize logger
	logger := utils.NewLogger()
	
	// Connect to database
	database, err := db.Connect(cfg)
	if err != nil {
		logger.Fatal("Failed to connect to database", "error", err)
	}
	
	// Initialize services
	engine := services.NewEngine(database, cfg, logger)
	
	// Initialize handlers
	templateHandler := handlers.NewTemplateHandler(database, logger)
	instanceHandler := handlers.NewInstanceHandler(database, engine, logger)
	
	// Start workflow engine
	go func() {
		if err := engine.Start(); err != nil {
			logger.Error("Failed to start workflow engine", "error", err)
		}
	}()
	
	// Setup Gin router
	if cfg.Environment == "production" {
		gin.SetMode(gin.ReleaseMode)
	}
	
	router := gin.New()
	router.Use(gin.Recovery())
	router.Use(middleware.Logger(logger))
	router.Use(middleware.CORS())
	
	// Health check endpoint
	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{
			"status":  "healthy",
			"service": "workflow-engine",
			"version": "1.0.0",
		})
	})
	
	// API routes
	v1 := router.Group("/api/v1")
	v1.Use(middleware.Auth(cfg.JWTSecret))
	{
		// Template routes
		templates := v1.Group("/templates")
		{
			templates.GET("", templateHandler.ListTemplates)
			templates.POST("", templateHandler.CreateTemplate)
			templates.GET("/:id", templateHandler.GetTemplate)
			templates.PUT("/:id", templateHandler.UpdateTemplate)
			templates.DELETE("/:id", templateHandler.DeleteTemplate)
		}
		
		// Instance routes
		instances := v1.Group("/instances")
		{
			instances.GET("", instanceHandler.ListInstances)
			instances.POST("", instanceHandler.CreateInstance)
			instances.GET("/:id", instanceHandler.GetInstance)
			instances.PUT("/:id/start", instanceHandler.StartInstance)
			instances.PUT("/:id/pause", instanceHandler.PauseInstance)
			instances.PUT("/:id/resume", instanceHandler.ResumeInstance)
			instances.PUT("/:id/cancel", instanceHandler.CancelInstance)
			instances.GET("/:id/steps", instanceHandler.GetInstanceSteps)
		}
		
		// Trigger routes
		triggers := v1.Group("/triggers")
		{
			triggers.POST("/webhook/:template_id", instanceHandler.TriggerWebhook)
		}
	}
	
	// Create HTTP server
	srv := &http.Server{
		Addr:         ":" + cfg.Port,
		Handler:      router,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 15 * time.Second,
		IdleTimeout:  60 * time.Second,
	}
	
	// Start server in goroutine
	go func() {
		logger.Info("Starting Workflow Engine", "port", cfg.Port)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Fatal("Failed to start server", "error", err)
		}
	}()
	
	// Wait for interrupt signal to gracefully shutdown the server
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit
	
	logger.Info("Shutting down server...")
	
	// Stop workflow engine
	engine.Stop()
	
	// Graceful shutdown with timeout
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	
	if err := srv.Shutdown(ctx); err != nil {
		logger.Fatal("Server forced to shutdown", "error", err)
	}
	
	logger.Info("Server exited")
}