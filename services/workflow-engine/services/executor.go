package services

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"
	"time"

	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"
	"gorm.io/gorm"

	"chorus/workflow-engine/config"
	"chorus/workflow-engine/models"
	"chorus/workflow-engine/utils"
)

type Executor struct {
	db     *gorm.DB
	redis  *redis.Client
	config *config.Config
	logger *utils.Logger
}

type StepResult struct {
	Success bool                   `json:"success"`
	Data    map[string]interface{} `json:"data"`
	Error   string                 `json:"error,omitempty"`
}

func NewExecutor(db *gorm.DB, redis *redis.Client, cfg *config.Config, logger *utils.Logger) *Executor {
	return &Executor{
		db:     db,
		redis:  redis,
		config: cfg,
		logger: logger,
	}
}

// ExecuteStep executes a single workflow step
func (e *Executor) ExecuteStep(instance *models.WorkflowInstance, stepDef *models.WorkflowStepDefinition) (*StepResult, error) {
	// Create or update step record
	step, err := e.createOrUpdateStep(instance.ID, stepDef)
	if err != nil {
		return nil, fmt.Errorf("failed to create step record: %w", err)
	}

	// Mark step as running
	now := time.Now()
	step.Status = models.StepStatusRunning
	step.StartedAt = &now

	if err := e.db.Save(step).Error; err != nil {
		return nil, fmt.Errorf("failed to update step status: %w", err)
	}

	e.logger.Info("Executing step", "instance_id", instance.ID, "step_id", stepDef.ID, "step_type", stepDef.Type)

	// Execute step based on type
	var result *StepResult
	switch stepDef.Type {
	case models.StepTypeAction:
		result, err = e.executeActionStep(instance, stepDef, step)
	case models.StepTypeCondition:
		result, err = e.executeConditionStep(instance, stepDef, step)
	case models.StepTypeParallel:
		result, err = e.executeParallelStep(instance, stepDef, step)
	case models.StepTypeWait:
		result, err = e.executeWaitStep(instance, stepDef, step)
	case models.StepTypeSubflow:
		result, err = e.executeSubflowStep(instance, stepDef, step)
	default:
		err = fmt.Errorf("unsupported step type: %s", stepDef.Type)
	}

	// Update step with result
	completedAt := time.Now()
	step.CompletedAt = &completedAt

	if err != nil {
		step.Status = models.StepStatusFailed
		step.ErrorData = models.JSONB{"error": err.Error()}
		result = &StepResult{Success: false, Error: err.Error()}
	} else {
		step.Status = models.StepStatusCompleted
		if result != nil {
			if resultData, jsonErr := json.Marshal(result.Data); jsonErr == nil {
				var jsonbData models.JSONB
				if json.Unmarshal(resultData, &jsonbData) == nil {
					step.OutputData = jsonbData
				}
			}
		}
	}

	if saveErr := e.db.Save(step).Error; saveErr != nil {
		e.logger.Error("Failed to save step result", "step_id", step.ID, "error", saveErr)
	}

	// Publish step completion event
	e.publishStepEvent("step_completed", instance.ID, stepDef.ID, result)

	return result, err
}

// executeActionStep executes an action step
func (e *Executor) executeActionStep(instance *models.WorkflowInstance, stepDef *models.WorkflowStepDefinition, step *models.WorkflowStep) (*StepResult, error) {
	action, ok := stepDef.Config["action"].(string)
	if !ok {
		return nil, fmt.Errorf("action not specified in step config")
	}

	switch action {
	case "http_request":
		return e.executeHTTPRequest(instance, stepDef, step)
	case "send_email":
		return e.executeSendEmail(instance, stepDef, step)
	case "log_message":
		return e.executeLogMessage(instance, stepDef, step)
	case "update_variables":
		return e.executeUpdateVariables(instance, stepDef, step)
	default:
		return nil, fmt.Errorf("unsupported action: %s", action)
	}
}

// executeConditionStep executes a condition step
func (e *Executor) executeConditionStep(instance *models.WorkflowInstance, stepDef *models.WorkflowStepDefinition, step *models.WorkflowStep) (*StepResult, error) {
	conditions := stepDef.Conditions
	if len(conditions) == 0 {
		return &StepResult{Success: false, Error: "no conditions defined"}, nil
	}

	// Evaluate all conditions (AND logic)
	for _, condition := range conditions {
		if !e.evaluateCondition(condition, instance.Variables) {
			return &StepResult{Success: false, Data: map[string]interface{}{"reason": "condition not met"}}, nil
		}
	}

	return &StepResult{Success: true, Data: map[string]interface{}{"reason": "all conditions met"}}, nil
}

// executeParallelStep executes parallel steps
func (e *Executor) executeParallelStep(instance *models.WorkflowInstance, stepDef *models.WorkflowStepDefinition, step *models.WorkflowStep) (*StepResult, error) {
	// For this implementation, we'll simulate parallel execution
	// In a production environment, you might use goroutines or separate workers
	
	parallelSteps, ok := stepDef.Config["parallel_steps"].([]interface{})
	if !ok {
		return nil, fmt.Errorf("parallel_steps not defined")
	}

	results := make(map[string]interface{})
	allSuccess := true

	for i, parallelStepData := range parallelSteps {
		stepName := fmt.Sprintf("parallel_%d", i)
		
		// Simulate step execution
		time.Sleep(100 * time.Millisecond)
		
		// For demo purposes, assume success
		results[stepName] = map[string]interface{}{
			"status": "completed",
			"data":   parallelStepData,
		}
	}

	return &StepResult{
		Success: allSuccess,
		Data:    results,
	}, nil
}

// executeWaitStep executes a wait step
func (e *Executor) executeWaitStep(instance *models.WorkflowInstance, stepDef *models.WorkflowStepDefinition, step *models.WorkflowStep) (*StepResult, error) {
	waitType, ok := stepDef.Config["wait_type"].(string)
	if !ok {
		return nil, fmt.Errorf("wait_type not specified")
	}

	switch waitType {
	case "duration":
		durationSec, ok := stepDef.Config["duration"].(float64)
		if !ok {
			return nil, fmt.Errorf("duration not specified for duration wait")
		}
		
		time.Sleep(time.Duration(durationSec) * time.Second)
		return &StepResult{Success: true, Data: map[string]interface{}{"waited": durationSec}}, nil
		
	case "event":
		eventName, ok := stepDef.Config["event"].(string)
		if !ok {
			return nil, fmt.Errorf("event not specified for event wait")
		}
		
		// For demo purposes, simulate waiting for an event
		e.logger.Info("Waiting for event", "event", eventName, "instance_id", instance.ID)
		
		// In a real implementation, this would wait for a Redis pub/sub event
		// For now, we'll just return success after a short delay
		time.Sleep(1 * time.Second)
		return &StepResult{Success: true, Data: map[string]interface{}{"event": eventName}}, nil
		
	default:
		return nil, fmt.Errorf("unsupported wait type: %s", waitType)
	}
}

// executeSubflowStep executes a subflow step
func (e *Executor) executeSubflowStep(instance *models.WorkflowInstance, stepDef *models.WorkflowStepDefinition, step *models.WorkflowStep) (*StepResult, error) {
	subflowID, ok := stepDef.Config["subflow_id"].(string)
	if !ok {
		return nil, fmt.Errorf("subflow_id not specified")
	}

	// In a real implementation, this would create a new workflow instance for the subflow
	// For demo purposes, we'll simulate subflow execution
	e.logger.Info("Executing subflow", "subflow_id", subflowID, "parent_instance", instance.ID)
	
	// Simulate subflow execution
	time.Sleep(500 * time.Millisecond)
	
	return &StepResult{
		Success: true,
		Data: map[string]interface{}{
			"subflow_id": subflowID,
			"status":     "completed",
		},
	}, nil
}

// executeHTTPRequest executes an HTTP request action
func (e *Executor) executeHTTPRequest(instance *models.WorkflowInstance, stepDef *models.WorkflowStepDefinition, step *models.WorkflowStep) (*StepResult, error) {
	url, ok := stepDef.Config["url"].(string)
	if !ok {
		return nil, fmt.Errorf("url not specified for HTTP request")
	}

	method, ok := stepDef.Config["method"].(string)
	if !ok {
		method = "GET"
	}

	// For demo purposes, simulate HTTP request
	e.logger.Info("Simulating HTTP request", "method", method, "url", url)
	time.Sleep(200 * time.Millisecond)

	return &StepResult{
		Success: true,
		Data: map[string]interface{}{
			"method":      method,
			"url":         url,
			"status_code": 200,
			"response":    "OK",
		},
	}, nil
}

// executeSendEmail executes a send email action
func (e *Executor) executeSendEmail(instance *models.WorkflowInstance, stepDef *models.WorkflowStepDefinition, step *models.WorkflowStep) (*StepResult, error) {
	to, ok := stepDef.Config["to"].(string)
	if !ok {
		return nil, fmt.Errorf("to address not specified for email")
	}

	subject, _ := stepDef.Config["subject"].(string)
	body, _ := stepDef.Config["body"].(string)

	// For demo purposes, simulate sending email
	e.logger.Info("Simulating email send", "to", to, "subject", subject, "body", body)
	time.Sleep(100 * time.Millisecond)

	return &StepResult{
		Success: true,
		Data: map[string]interface{}{
			"to":      to,
			"subject": subject,
			"sent":    true,
		},
	}, nil
}

// executeLogMessage executes a log message action
func (e *Executor) executeLogMessage(instance *models.WorkflowInstance, stepDef *models.WorkflowStepDefinition, step *models.WorkflowStep) (*StepResult, error) {
	message, ok := stepDef.Config["message"].(string)
	if !ok {
		return nil, fmt.Errorf("message not specified for log action")
	}

	level, ok := stepDef.Config["level"].(string)
	if !ok {
		level = "info"
	}

	// Log the message
	switch level {
	case "error":
		e.logger.Error(message, "instance_id", instance.ID, "step_id", stepDef.ID)
	case "warn":
		e.logger.Warn(message, "instance_id", instance.ID, "step_id", stepDef.ID)
	case "debug":
		e.logger.Debug(message, "instance_id", instance.ID, "step_id", stepDef.ID)
	default:
		e.logger.Info(message, "instance_id", instance.ID, "step_id", stepDef.ID)
	}

	return &StepResult{
		Success: true,
		Data: map[string]interface{}{
			"message": message,
			"level":   level,
			"logged":  true,
		},
	}, nil
}

// executeUpdateVariables executes an update variables action
func (e *Executor) executeUpdateVariables(instance *models.WorkflowInstance, stepDef *models.WorkflowStepDefinition, step *models.WorkflowStep) (*StepResult, error) {
	updates, ok := stepDef.Config["updates"].(map[string]interface{})
	if !ok {
		return nil, fmt.Errorf("updates not specified for update variables action")
	}

	// Update instance variables
	if instance.Variables == nil {
		instance.Variables = make(models.JSONB)
	}

	for key, value := range updates {
		instance.Variables[key] = value
	}

	// Save updated variables
	if err := e.db.Model(&models.WorkflowInstance{}).
		Where("id = ?", instance.ID).
		Update("variables", instance.Variables).Error; err != nil {
		return nil, fmt.Errorf("failed to update variables: %w", err)
	}

	return &StepResult{
		Success: true,
		Data: map[string]interface{}{
			"updated_variables": updates,
		},
	}, nil
}

// Helper methods

func (e *Executor) createOrUpdateStep(instanceID uuid.UUID, stepDef *models.WorkflowStepDefinition) (*models.WorkflowStep, error) {
	var step models.WorkflowStep
	
	// Try to find existing step
	err := e.db.Where("instance_id = ? AND step_id = ?", instanceID, stepDef.ID).First(&step).Error
	if err == gorm.ErrRecordNotFound {
		// Create new step
		step = models.WorkflowStep{
			InstanceID: instanceID,
			StepID:     stepDef.ID,
			StepType:   stepDef.Type,
			Status:     models.StepStatusPending,
			InputData:  make(models.JSONB),
		}
		
		// Set input data from step config
		if configData, err := json.Marshal(stepDef.Config); err == nil {
			json.Unmarshal(configData, &step.InputData)
		}
		
		if err := e.db.Create(&step).Error; err != nil {
			return nil, err
		}
	} else if err != nil {
		return nil, err
	}
	
	return &step, nil
}

func (e *Executor) evaluateCondition(condition models.StepCondition, variables models.JSONB) bool {
	value, exists := variables[condition.Field]
	if !exists {
		return false
	}

	switch condition.Operator {
	case "eq", "equals":
		return value == condition.Value
	case "ne", "not_equals":
		return value != condition.Value
	case "gt", "greater_than":
		if vFloat, ok := value.(float64); ok {
			if cFloat, ok := condition.Value.(float64); ok {
				return vFloat > cFloat
			}
		}
	case "lt", "less_than":
		if vFloat, ok := value.(float64); ok {
			if cFloat, ok := condition.Value.(float64); ok {
				return vFloat < cFloat
			}
		}
	case "contains":
		if vStr, ok := value.(string); ok {
			if cStr, ok := condition.Value.(string); ok {
				return strings.Contains(vStr, cStr)
			}
		}
	}

	return false
}

func (e *Executor) publishStepEvent(eventType string, instanceID uuid.UUID, stepID string, result *StepResult) {
	event := map[string]interface{}{
		"type":        eventType,
		"instance_id": instanceID.String(),
		"step_id":     stepID,
		"timestamp":   time.Now().Unix(),
	}

	if result != nil {
		event["success"] = result.Success
		if result.Error != "" {
			event["error"] = result.Error
		}
	}

	if eventData, err := json.Marshal(event); err == nil {
		e.redis.Publish(context.Background(), "workflow:events", string(eventData))
	}
}

// HandleStepTimeout handles step timeouts
func (e *Executor) HandleStepTimeout(step *models.WorkflowStep) {
	// Check if step can be retried
	var retryPolicy *models.RetryPolicy
	// In a real implementation, you would load this from the step definition
	
	if retryPolicy != nil && step.RetryCount < retryPolicy.MaxRetries {
		// Retry the step
		step.RetryCount++
		step.Status = models.StepStatusPending
		step.StartedAt = nil
		step.CompletedAt = nil
		step.ErrorData = nil
		
		if err := e.db.Save(step).Error; err != nil {
			e.logger.Error("Failed to retry step", "step_id", step.ID, "error", err)
		} else {
			e.logger.Info("Step retried", "step_id", step.ID, "retry_count", step.RetryCount)
		}
	} else {
		// Mark step as failed
		now := time.Now()
		step.Status = models.StepStatusFailed
		step.CompletedAt = &now
		step.ErrorData = models.JSONB{"error": "step timed out"}
		
		if err := e.db.Save(step).Error; err != nil {
			e.logger.Error("Failed to fail timed out step", "step_id", step.ID, "error", err)
		}
	}
}