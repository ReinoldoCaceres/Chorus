package models

import (
	"database/sql/driver"
	"encoding/json"
	"time"

	"github.com/google/uuid"
)

// JSONB type for PostgreSQL JSONB fields
type JSONB map[string]interface{}

func (j JSONB) Value() (driver.Value, error) {
	return json.Marshal(j)
}

func (j *JSONB) Scan(value interface{}) error {
	if value == nil {
		*j = make(JSONB)
		return nil
	}
	
	bytes, ok := value.([]byte)
	if !ok {
		return nil
	}
	
	return json.Unmarshal(bytes, j)
}

// WorkflowTemplate represents a workflow template
type WorkflowTemplate struct {
	ID          uuid.UUID `json:"id" gorm:"type:uuid;primary_key;default:uuid_generate_v4()"`
	Name        string    `json:"name" gorm:"not null" binding:"required"`
	Description string    `json:"description"`
	Category    string    `json:"category"`
	Version     string    `json:"version" gorm:"default:1.0.0"`
	Schema      JSONB     `json:"schema" gorm:"type:jsonb;not null" binding:"required"`
	Metadata    JSONB     `json:"metadata" gorm:"type:jsonb;default:'{}'"`
	IsActive    bool      `json:"is_active" gorm:"default:true"`
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at"`
	CreatedBy   string    `json:"created_by"`
}

func (WorkflowTemplate) TableName() string {
	return "workflow.templates"
}

// WorkflowInstance represents a workflow instance
type WorkflowInstance struct {
	ID          uuid.UUID         `json:"id" gorm:"type:uuid;primary_key;default:uuid_generate_v4()"`
	TemplateID  uuid.UUID         `json:"template_id" gorm:"type:uuid;not null" binding:"required"`
	Name        string            `json:"name" gorm:"not null" binding:"required"`
	Status      WorkflowStatus    `json:"status" gorm:"default:pending"`
	Context     JSONB             `json:"context" gorm:"type:jsonb;default:'{}'"`
	Variables   JSONB             `json:"variables" gorm:"type:jsonb;default:'{}'"`
	CurrentStep string            `json:"current_step"`
	StartedAt   *time.Time        `json:"started_at"`
	CompletedAt *time.Time        `json:"completed_at"`
	ErrorMessage string           `json:"error_message"`
	CreatedAt   time.Time         `json:"created_at"`
	UpdatedAt   time.Time         `json:"updated_at"`
	CreatedBy   string            `json:"created_by"`
	
	// Relations
	Template WorkflowTemplate `json:"template,omitempty" gorm:"foreignKey:TemplateID"`
	Steps    []WorkflowStep   `json:"steps,omitempty" gorm:"foreignKey:InstanceID"`
}

func (WorkflowInstance) TableName() string {
	return "workflow.instances"
}

// WorkflowStep represents a workflow step execution
type WorkflowStep struct {
	ID          uuid.UUID   `json:"id" gorm:"type:uuid;primary_key;default:uuid_generate_v4()"`
	InstanceID  uuid.UUID   `json:"instance_id" gorm:"type:uuid;not null"`
	StepID      string      `json:"step_id" gorm:"not null"`
	StepType    StepType    `json:"step_type" gorm:"not null"`
	Status      StepStatus  `json:"status" gorm:"default:pending"`
	InputData   JSONB       `json:"input_data" gorm:"type:jsonb;default:'{}'"`
	OutputData  JSONB       `json:"output_data" gorm:"type:jsonb;default:'{}'"`
	ErrorData   JSONB       `json:"error_data" gorm:"type:jsonb"`
	StartedAt   *time.Time  `json:"started_at"`
	CompletedAt *time.Time  `json:"completed_at"`
	RetryCount  int         `json:"retry_count" gorm:"default:0"`
	CreatedAt   time.Time   `json:"created_at"`
	UpdatedAt   time.Time   `json:"updated_at"`
	
	// Relations
	Instance WorkflowInstance `json:"instance,omitempty" gorm:"foreignKey:InstanceID"`
}

func (WorkflowStep) TableName() string {
	return "workflow.steps"
}

// WorkflowTrigger represents a workflow trigger
type WorkflowTrigger struct {
	ID              uuid.UUID     `json:"id" gorm:"type:uuid;primary_key;default:uuid_generate_v4()"`
	TemplateID      uuid.UUID     `json:"template_id" gorm:"type:uuid;not null"`
	TriggerType     TriggerType   `json:"trigger_type" gorm:"not null"`
	TriggerConfig   JSONB         `json:"trigger_config" gorm:"type:jsonb;not null"`
	IsActive        bool          `json:"is_active" gorm:"default:true"`
	LastTriggeredAt *time.Time    `json:"last_triggered_at"`
	CreatedAt       time.Time     `json:"created_at"`
	UpdatedAt       time.Time     `json:"updated_at"`
	
	// Relations
	Template WorkflowTemplate `json:"template,omitempty" gorm:"foreignKey:TemplateID"`
}

func (WorkflowTrigger) TableName() string {
	return "workflow.triggers"
}

// Enums
type WorkflowStatus string

const (
	WorkflowStatusPending   WorkflowStatus = "pending"
	WorkflowStatusRunning   WorkflowStatus = "running"
	WorkflowStatusCompleted WorkflowStatus = "completed"
	WorkflowStatusFailed    WorkflowStatus = "failed"
	WorkflowStatusCancelled WorkflowStatus = "cancelled"
	WorkflowStatusPaused    WorkflowStatus = "paused"
)

type StepStatus string

const (
	StepStatusPending   StepStatus = "pending"
	StepStatusRunning   StepStatus = "running"
	StepStatusCompleted StepStatus = "completed"
	StepStatusFailed    StepStatus = "failed"
	StepStatusSkipped   StepStatus = "skipped"
)

type StepType string

const (
	StepTypeAction    StepType = "action"
	StepTypeCondition StepType = "condition"
	StepTypeParallel  StepType = "parallel"
	StepTypeWait      StepType = "wait"
	StepTypeSubflow   StepType = "subflow"
)

type TriggerType string

const (
	TriggerTypeManual    TriggerType = "manual"
	TriggerTypeSchedule  TriggerType = "schedule"
	TriggerTypeEvent     TriggerType = "event"
	TriggerTypeWebhook   TriggerType = "webhook"
	TriggerTypeCondition TriggerType = "condition"
)

// Request/Response DTOs
type CreateTemplateRequest struct {
	Name        string `json:"name" binding:"required"`
	Description string `json:"description"`
	Category    string `json:"category"`
	Version     string `json:"version"`
	Schema      JSONB  `json:"schema" binding:"required"`
	Metadata    JSONB  `json:"metadata"`
}

type UpdateTemplateRequest struct {
	Name        *string `json:"name"`
	Description *string `json:"description"`
	Category    *string `json:"category"`
	Schema      *JSONB  `json:"schema"`
	Metadata    *JSONB  `json:"metadata"`
	IsActive    *bool   `json:"is_active"`
}

type CreateInstanceRequest struct {
	TemplateID uuid.UUID `json:"template_id" binding:"required"`
	Name       string    `json:"name" binding:"required"`
	Variables  JSONB     `json:"variables"`
	Context    JSONB     `json:"context"`
}

type TriggerWebhookRequest struct {
	Variables JSONB `json:"variables"`
	Context   JSONB `json:"context"`
}

type ListResponse[T any] struct {
	Data       []T   `json:"data"`
	Total      int64 `json:"total"`
	Page       int   `json:"page"`
	PageSize   int   `json:"page_size"`
	TotalPages int   `json:"total_pages"`
}

// WorkflowSchema represents the structure of a workflow definition
type WorkflowSchema struct {
	Steps []WorkflowStepDefinition `json:"steps"`
}

type WorkflowStepDefinition struct {
	ID          string                 `json:"id"`
	Name        string                 `json:"name"`
	Type        StepType               `json:"type"`
	Config      map[string]interface{} `json:"config"`
	NextSteps   []string               `json:"next_steps,omitempty"`
	Conditions  []StepCondition        `json:"conditions,omitempty"`
	RetryPolicy *RetryPolicy           `json:"retry_policy,omitempty"`
}

type StepCondition struct {
	Field    string      `json:"field"`
	Operator string      `json:"operator"`
	Value    interface{} `json:"value"`
}

type RetryPolicy struct {
	MaxRetries int `json:"max_retries"`
	Delay      int `json:"delay"` // in seconds
}