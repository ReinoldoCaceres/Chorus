package db

import (
	"fmt"
	"time"

	"gorm.io/driver/postgres"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"

	"chorus/workflow-engine/config"
	"chorus/workflow-engine/models"
)

// Connect establishes a connection to the PostgreSQL database
func Connect(cfg *config.Config) (*gorm.DB, error) {
	// Configure GORM logger
	var gormLogger logger.Interface
	if cfg.Environment == "production" {
		gormLogger = logger.Default.LogMode(logger.Silent)
	} else {
		gormLogger = logger.Default.LogMode(logger.Info)
	}

	// Open database connection
	db, err := gorm.Open(postgres.Open(cfg.DatabaseURL), &gorm.Config{
		Logger: gormLogger,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to connect to database: %w", err)
	}

	// Configure connection pool
	sqlDB, err := db.DB()
	if err != nil {
		return nil, fmt.Errorf("failed to get underlying sql.DB: %w", err)
	}

	// Set connection pool settings
	sqlDB.SetMaxIdleConns(10)
	sqlDB.SetMaxOpenConns(100)
	sqlDB.SetConnMaxLifetime(time.Hour)

	// Test the connection
	if err := sqlDB.Ping(); err != nil {
		return nil, fmt.Errorf("failed to ping database: %w", err)
	}

	// Auto-migrate models (optional - the tables should already exist from init.sql)
	if cfg.Environment == "development" {
		if err := autoMigrate(db); err != nil {
			return nil, fmt.Errorf("failed to auto-migrate: %w", err)
		}
	}

	return db, nil
}

// autoMigrate runs automatic database migrations
func autoMigrate(db *gorm.DB) error {
	// Set the search path to include the workflow schema
	if err := db.Exec("SET search_path TO public, workflow").Error; err != nil {
		return fmt.Errorf("failed to set search path: %w", err)
	}

	// Auto-migrate all models
	models := []interface{}{
		&models.WorkflowTemplate{},
		&models.WorkflowInstance{},
		&models.WorkflowStep{},
		&models.WorkflowTrigger{},
	}

	for _, model := range models {
		if err := db.AutoMigrate(model); err != nil {
			return fmt.Errorf("failed to migrate %T: %w", model, err)
		}
	}

	return nil
}

// GetDatabase returns a database instance with the correct schema search path
func GetDatabase(db *gorm.DB) *gorm.DB {
	// Ensure we're using the correct search path for workflow operations
	return db.Exec("SET search_path TO public, workflow")
}