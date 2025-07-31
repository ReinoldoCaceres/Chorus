package services

import (
	"context"
	"encoding/json"
	"fmt"
	"sync"
	"time"

	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"
	"gorm.io/gorm"

	"chorus/workflow-engine/config"
	"chorus/workflow-engine/models"
	"chorus/workflow-engine/utils"
)

type Engine struct {
	db       *gorm.DB
	redis    *redis.Client
	config   *config.Config
	logger   *utils.Logger
	executor *Executor

	// Internal state
	ctx       context.Context
	cancel    context.CancelFunc
	wg        sync.WaitGroup
	instances sync.Map // Map of running instance IDs
	queue     chan uuid.UUID
}

func NewEngine(db *gorm.DB, cfg *config.Config, logger *utils.Logger) *Engine {
	ctx, cancel := context.WithCancel(context.Background())

	// Initialize Redis client
	opt, err := redis.ParseURL(cfg.RedisURL)
	if err != nil {
		logger.Fatal("Failed to parse Redis URL", "error", err)
	}
	redisClient := redis.NewClient(opt)

	// Test Redis connection
	if err := redisClient.Ping(ctx).Err(); err != nil {
		logger.Fatal("Failed to connect to Redis", "error", err)
	}

	engine := &Engine{
		db:     db,
		redis:  redisClient,
		config: cfg,
		logger: logger,
		ctx:    ctx,
		cancel: cancel,
		queue:  make(chan uuid.UUID, cfg.MaxConcurrentWorkflows),
	}

	engine.executor = NewExecutor(db, redisClient, cfg, logger)

	return engine
}

// Start begins the workflow engine processing
func (e *Engine) Start() error {
	e.logger.Info("Starting workflow engine")

	// Start the main processing loop
	e.wg.Add(1)
	go e.processQueue()

	// Start the periodic checker for pending workflows
	e.wg.Add(1)
	go e.periodicChecker()

	// Start Redis event listener for workflow events
	e.wg.Add(1)
	go e.eventListener()

	return nil
}

// Stop gracefully shuts down the workflow engine
func (e *Engine) Stop() {
	e.logger.Info("Stopping workflow engine")

	// Cancel context to signal shutdown
	e.cancel()

	// Wait for all goroutines to finish
	e.wg.Wait()

	// Close Redis connection
	if err := e.redis.Close(); err != nil {
		e.logger.Error("Failed to close Redis connection", "error", err)
	}

	e.logger.Info("Workflow engine stopped")
}

// QueueInstance queues a workflow instance for execution
func (e *Engine) QueueInstance(instanceID uuid.UUID) error {
	select {
	case e.queue <- instanceID:
		e.logger.Debug("Instance queued", "instance_id", instanceID)
		return nil
	default:
		return fmt.Errorf("workflow queue is full")
	}
}

// processQueue processes queued workflow instances
func (e *Engine) processQueue() {
	defer e.wg.Done()

	for {
		select {
		case <-e.ctx.Done():
			return
		case instanceID := <-e.queue:
			// Check if instance is already running
			if _, running := e.instances.Load(instanceID); running {
				e.logger.Debug("Instance already running", "instance_id", instanceID)
				continue
			}

			// Start processing instance in a separate goroutine
			e.wg.Add(1)
			go e.processInstance(instanceID)
		}
	}
}

// processInstance processes a single workflow instance
func (e *Engine) processInstance(instanceID uuid.UUID) {
	defer e.wg.Done()

	// Mark instance as running
	e.instances.Store(instanceID, true)
	defer e.instances.Delete(instanceID)

	e.logger.Info("Starting workflow instance", "instance_id", instanceID)

	// Load instance with template
	var instance models.WorkflowInstance
	if err := e.db.Preload("Template").First(&instance, instanceID).Error; err != nil {
		e.logger.Error("Failed to load instance", "instance_id", instanceID, "error", err)
		return
	}

	// Check if instance should be processed
	if instance.Status != models.WorkflowStatusRunning {
		e.logger.Debug("Instance not in running state", "instance_id", instanceID, "status", instance.Status)
		return
	}

	// Parse workflow schema
	var schema models.WorkflowSchema
	if err := e.parseSchema(instance.Template.Schema, &schema); err != nil {
		e.logger.Error("Failed to parse workflow schema", "instance_id", instanceID, "error", err)
		e.failInstance(instanceID, fmt.Sprintf("Invalid workflow schema: %v", err))
		return
	}

	// Execute workflow
	if err := e.executeWorkflow(&instance, &schema); err != nil {
		e.logger.Error("Workflow execution failed", "instance_id", instanceID, "error", err)
		e.failInstance(instanceID, err.Error())
		return
	}

	e.logger.Info("Workflow instance completed", "instance_id", instanceID)
}

// executeWorkflow executes a workflow instance
func (e *Engine) executeWorkflow(instance *models.WorkflowInstance, schema *models.WorkflowSchema) error {
	if len(schema.Steps) == 0 {
		return e.completeInstance(instance.ID)
	}

	// Find the starting step
	currentStepID := instance.CurrentStep
	if currentStepID == "" {
		currentStepID = schema.Steps[0].ID
	}

	for {
		// Check if workflow was cancelled or paused
		if err := e.checkInstanceStatus(instance.ID); err != nil {
			return err
		}

		// Find current step definition
		stepDef := e.findStepDefinition(schema.Steps, currentStepID)
		if stepDef == nil {
			return fmt.Errorf("step definition not found: %s", currentStepID)
		}

		// Execute step
		stepResult, err := e.executor.ExecuteStep(instance, stepDef)
		if err != nil {
			return fmt.Errorf("step execution failed: %w", err)
		}

		// Update instance current step
		if err := e.updateInstanceCurrentStep(instance.ID, currentStepID); err != nil {
			e.logger.Error("Failed to update current step", "instance_id", instance.ID, "step", currentStepID, "error", err)
		}

		// Determine next step
		nextStepID, err := e.determineNextStep(stepDef, stepResult)
		if err != nil {
			return fmt.Errorf("failed to determine next step: %w", err)
		}

		if nextStepID == "" {
			// Workflow completed
			return e.completeInstance(instance.ID)
		}

		currentStepID = nextStepID

		// Add a small delay to prevent tight loops
		select {
		case <-e.ctx.Done():
			return fmt.Errorf("workflow engine shutting down")
		case <-time.After(100 * time.Millisecond):
		}
	}
}

// periodicChecker periodically checks for pending workflows and timeouts
func (e *Engine) periodicChecker() {
	defer e.wg.Done()

	ticker := time.NewTicker(time.Duration(e.config.WorkflowCheckInterval) * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-e.ctx.Done():
			return
		case <-ticker.C:
			e.checkPendingWorkflows()
			e.checkTimeouts()
		}
	}
}

// eventListener listens for Redis pub/sub events
func (e *Engine) eventListener() {
	defer e.wg.Done()

	pubsub := e.redis.Subscribe(e.ctx, "workflow:events")
	defer pubsub.Close()

	for {
		select {
		case <-e.ctx.Done():
			return
		default:
			msg, err := pubsub.ReceiveMessage(e.ctx)
			if err != nil {
				if err != context.Canceled {
					e.logger.Error("Redis pubsub error", "error", err)
				}
				continue
			}

			e.handleEvent(msg.Payload)
		}
	}
}

// Helper methods

func (e *Engine) parseSchema(schemaData models.JSONB, schema *models.WorkflowSchema) error {
	data, err := json.Marshal(schemaData)
	if err != nil {
		return err
	}

	return json.Unmarshal(data, schema)
}

func (e *Engine) findStepDefinition(steps []models.WorkflowStepDefinition, stepID string) *models.WorkflowStepDefinition {
	for _, step := range steps {
		if step.ID == stepID {
			return &step
		}
	}
	return nil
}

func (e *Engine) determineNextStep(stepDef *models.WorkflowStepDefinition, result *StepResult) (string, error) {
	if len(stepDef.NextSteps) == 0 {
		return "", nil // End of workflow
	}

	if len(stepDef.NextSteps) == 1 {
		return stepDef.NextSteps[0], nil
	}

	// Handle conditional logic
	if stepDef.Type == models.StepTypeCondition {
		if result.Success {
			if len(stepDef.NextSteps) > 0 {
				return stepDef.NextSteps[0], nil
			}
		} else {
			if len(stepDef.NextSteps) > 1 {
				return stepDef.NextSteps[1], nil
			}
		}
	}

	// Default to first next step
	return stepDef.NextSteps[0], nil
}

func (e *Engine) checkInstanceStatus(instanceID uuid.UUID) error {
	var instance models.WorkflowInstance
	if err := e.db.Select("status").First(&instance, instanceID).Error; err != nil {
		return err
	}

	if instance.Status != models.WorkflowStatusRunning {
		return fmt.Errorf("workflow instance status changed to %s", instance.Status)
	}

	return nil
}

func (e *Engine) updateInstanceCurrentStep(instanceID uuid.UUID, stepID string) error {
	return e.db.Model(&models.WorkflowInstance{}).
		Where("id = ?", instanceID).
		Update("current_step", stepID).Error
}

func (e *Engine) completeInstance(instanceID uuid.UUID) error {
	now := time.Now()
	return e.db.Model(&models.WorkflowInstance{}).
		Where("id = ?", instanceID).
		Updates(map[string]interface{}{
			"status":       models.WorkflowStatusCompleted,
			"completed_at": now,
		}).Error
}

func (e *Engine) failInstance(instanceID uuid.UUID, errorMsg string) {
	now := time.Now()
	if err := e.db.Model(&models.WorkflowInstance{}).
		Where("id = ?", instanceID).
		Updates(map[string]interface{}{
			"status":        models.WorkflowStatusFailed,
			"completed_at":  now,
			"error_message": errorMsg,
		}).Error; err != nil {
		e.logger.Error("Failed to update failed instance", "instance_id", instanceID, "error", err)
	}
}

func (e *Engine) checkPendingWorkflows() {
	var instances []models.WorkflowInstance
	if err := e.db.Where("status = ?", models.WorkflowStatusPending).
		Limit(10).Find(&instances).Error; err != nil {
		e.logger.Error("Failed to fetch pending workflows", "error", err)
		return
	}

	for _, instance := range instances {
		if err := e.QueueInstance(instance.ID); err != nil {
			e.logger.Error("Failed to queue pending instance", "instance_id", instance.ID, "error", err)
		}
	}
}

func (e *Engine) checkTimeouts() {
	timeout := time.Now().Add(-time.Duration(e.config.StepTimeout) * time.Second)

	// Find running steps that have timed out
	var steps []models.WorkflowStep
	if err := e.db.Where("status = ? AND started_at < ?", models.StepStatusRunning, timeout).
		Find(&steps).Error; err != nil {
		e.logger.Error("Failed to fetch timed out steps", "error", err)
		return
	}

	for _, step := range steps {
		e.logger.Warn("Step timed out", "step_id", step.ID, "instance_id", step.InstanceID)
		// Handle timeout - could retry or fail the step
		e.executor.HandleStepTimeout(&step)
	}
}

func (e *Engine) handleEvent(payload string) {
	var event map[string]interface{}
	if err := json.Unmarshal([]byte(payload), &event); err != nil {
		e.logger.Error("Failed to parse event", "error", err)
		return
	}

	eventType, ok := event["type"].(string)
	if !ok {
		return
	}

	switch eventType {
	case "step_completed":
		// Handle step completion events
		if instanceIDStr, ok := event["instance_id"].(string); ok {
			if instanceID, err := uuid.Parse(instanceIDStr); err == nil {
				if err := e.QueueInstance(instanceID); err != nil {
					e.logger.Error("Failed to queue instance after step completion", "instance_id", instanceID, "error", err)
				}
			}
		}
	case "workflow_triggered":
		// Handle external workflow triggers
		e.logger.Info("Workflow triggered", "event", event)
	}
}