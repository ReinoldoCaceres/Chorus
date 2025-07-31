package handlers

import (
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"gorm.io/gorm"

	"chorus/workflow-engine/models"
	"chorus/workflow-engine/services"
	"chorus/workflow-engine/utils"
)

type InstanceHandler struct {
	db     *gorm.DB
	engine *services.Engine
	logger *utils.Logger
}

func NewInstanceHandler(db *gorm.DB, engine *services.Engine, logger *utils.Logger) *InstanceHandler {
	return &InstanceHandler{
		db:     db,
		engine: engine,
		logger: logger,
	}
}

// ListInstances handles GET /api/v1/instances
func (h *InstanceHandler) ListInstances(c *gin.Context) {
	// Parse query parameters
	page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
	pageSize, _ := strconv.Atoi(c.DefaultQuery("page_size", "20"))
	status := c.Query("status")
	templateID := c.Query("template_id")

	if page < 1 {
		page = 1
	}
	if pageSize < 1 || pageSize > 100 {
		pageSize = 20
	}

	// Build query
	query := h.db.Model(&models.WorkflowInstance{}).Preload("Template")

	if status != "" {
		query = query.Where("status = ?", status)
	}
	if templateID != "" {
		if tid, err := uuid.Parse(templateID); err == nil {
			query = query.Where("template_id = ?", tid)
		}
	}

	// Get total count
	var total int64
	if err := query.Count(&total).Error; err != nil {
		h.logger.Error("Failed to count instances", "error", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to count instances",
		})
		return
	}

	// Get instances with pagination
	var instances []models.WorkflowInstance
	offset := (page - 1) * pageSize
	if err := query.Offset(offset).Limit(pageSize).Order("created_at DESC").Find(&instances).Error; err != nil {
		h.logger.Error("Failed to fetch instances", "error", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to fetch instances",
		})
		return
	}

	totalPages := int((total + int64(pageSize) - 1) / int64(pageSize))

	response := models.ListResponse[models.WorkflowInstance]{
		Data:       instances,
		Total:      total,
		Page:       page,
		PageSize:   pageSize,
		TotalPages: totalPages,
	}

	c.JSON(http.StatusOK, response)
}

// CreateInstance handles POST /api/v1/instances
func (h *InstanceHandler) CreateInstance(c *gin.Context) {
	var req models.CreateInstanceRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid request body",
			"details": err.Error(),
		})
		return
	}

	// Validate template exists and is active
	var template models.WorkflowTemplate
	if err := h.db.Where("id = ? AND is_active = true", req.TemplateID).First(&template).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			c.JSON(http.StatusNotFound, gin.H{
				"error": "Template not found or inactive",
			})
			return
		}
		h.logger.Error("Failed to fetch template", "error", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to fetch template",
		})
		return
	}

	// Get user ID from context
	userID, _ := c.Get("userID")

	instance := models.WorkflowInstance{
		TemplateID: req.TemplateID,
		Name:       req.Name,
		Variables:  req.Variables,
		Context:    req.Context,
		Status:     models.WorkflowStatusPending,
		CreatedBy:  userID.(string),
	}

	if instance.Variables == nil {
		instance.Variables = make(models.JSONB)
	}
	if instance.Context == nil {
		instance.Context = make(models.JSONB)
	}

	if err := h.db.Create(&instance).Error; err != nil {
		h.logger.Error("Failed to create instance", "error", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to create instance",
		})
		return
	}

	// Load the template for the response
	instance.Template = template

	h.logger.Info("Instance created", "id", instance.ID, "name", instance.Name, "template", template.Name)
	c.JSON(http.StatusCreated, instance)
}

// GetInstance handles GET /api/v1/instances/:id
func (h *InstanceHandler) GetInstance(c *gin.Context) {
	id := c.Param("id")
	instanceID, err := uuid.Parse(id)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid instance ID",
		})
		return
	}

	var instance models.WorkflowInstance
	if err := h.db.Preload("Template").Preload("Steps").First(&instance, instanceID).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			c.JSON(http.StatusNotFound, gin.H{
				"error": "Instance not found",
			})
			return
		}
		h.logger.Error("Failed to fetch instance", "error", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to fetch instance",
		})
		return
	}

	c.JSON(http.StatusOK, instance)
}

// StartInstance handles PUT /api/v1/instances/:id/start
func (h *InstanceHandler) StartInstance(c *gin.Context) {
	id := c.Param("id")
	instanceID, err := uuid.Parse(id)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid instance ID",
		})
		return
	}

	var instance models.WorkflowInstance
	if err := h.db.First(&instance, instanceID).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			c.JSON(http.StatusNotFound, gin.H{
				"error": "Instance not found",
			})
			return
		}
		h.logger.Error("Failed to fetch instance", "error", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to fetch instance",
		})
		return
	}

	// Check if instance can be started
	if instance.Status != models.WorkflowStatusPending && instance.Status != models.WorkflowStatusPaused {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Instance cannot be started in current status",
			"current_status": instance.Status,
		})
		return
	}

	// Update instance status and started_at
	now := time.Now()
	instance.Status = models.WorkflowStatusRunning
	instance.StartedAt = &now

	if err := h.db.Save(&instance).Error; err != nil {
		h.logger.Error("Failed to update instance", "error", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to update instance",
		})
		return
	}

	// Queue instance for execution
	if err := h.engine.QueueInstance(instanceID); err != nil {
		h.logger.Error("Failed to queue instance", "error", err, "instance_id", instanceID)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to queue instance for execution",
		})
		return
	}

	h.logger.Info("Instance started", "id", instance.ID, "name", instance.Name)
	c.JSON(http.StatusOK, instance)
}

// PauseInstance handles PUT /api/v1/instances/:id/pause
func (h *InstanceHandler) PauseInstance(c *gin.Context) {
	id := c.Param("id")
	instanceID, err := uuid.Parse(id)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid instance ID",
		})
		return
	}

	var instance models.WorkflowInstance
	if err := h.db.First(&instance, instanceID).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			c.JSON(http.StatusNotFound, gin.H{
				"error": "Instance not found",
			})
			return
		}
		h.logger.Error("Failed to fetch instance", "error", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to fetch instance",
		})
		return
	}

	// Check if instance can be paused
	if instance.Status != models.WorkflowStatusRunning {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Instance cannot be paused in current status",
			"current_status": instance.Status,
		})
		return
	}

	// Update instance status
	instance.Status = models.WorkflowStatusPaused

	if err := h.db.Save(&instance).Error; err != nil {
		h.logger.Error("Failed to update instance", "error", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to update instance",
		})
		return
	}

	h.logger.Info("Instance paused", "id", instance.ID, "name", instance.Name)
	c.JSON(http.StatusOK, instance)
}

// ResumeInstance handles PUT /api/v1/instances/:id/resume
func (h *InstanceHandler) ResumeInstance(c *gin.Context) {
	id := c.Param("id")
	instanceID, err := uuid.Parse(id)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid instance ID",
		})
		return
	}

	var instance models.WorkflowInstance
	if err := h.db.First(&instance, instanceID).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			c.JSON(http.StatusNotFound, gin.H{
				"error": "Instance not found",
			})
			return
		}
		h.logger.Error("Failed to fetch instance", "error", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to fetch instance",
		})
		return
	}

	// Check if instance can be resumed
	if instance.Status != models.WorkflowStatusPaused {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Instance cannot be resumed in current status",
			"current_status": instance.Status,
		})
		return
	}

	// Update instance status
	instance.Status = models.WorkflowStatusRunning

	if err := h.db.Save(&instance).Error; err != nil {
		h.logger.Error("Failed to update instance", "error", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to update instance",
		})
		return
	}

	// Queue instance for execution
	if err := h.engine.QueueInstance(instanceID); err != nil {
		h.logger.Error("Failed to queue instance", "error", err, "instance_id", instanceID)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to queue instance for execution",
		})
		return
	}

	h.logger.Info("Instance resumed", "id", instance.ID, "name", instance.Name)
	c.JSON(http.StatusOK, instance)
}

// CancelInstance handles PUT /api/v1/instances/:id/cancel
func (h *InstanceHandler) CancelInstance(c *gin.Context) {
	id := c.Param("id")
	instanceID, err := uuid.Parse(id)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid instance ID",
		})
		return
	}

	var instance models.WorkflowInstance
	if err := h.db.First(&instance, instanceID).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			c.JSON(http.StatusNotFound, gin.H{
				"error": "Instance not found",
			})
			return
		}
		h.logger.Error("Failed to fetch instance", "error", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to fetch instance",
		})
		return
	}

	// Check if instance can be cancelled
	if instance.Status == models.WorkflowStatusCompleted || instance.Status == models.WorkflowStatusFailed || instance.Status == models.WorkflowStatusCancelled {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Instance cannot be cancelled in current status",
			"current_status": instance.Status,
		})
		return
	}

	// Update instance status
	now := time.Now()
	instance.Status = models.WorkflowStatusCancelled
	instance.CompletedAt = &now

	if err := h.db.Save(&instance).Error; err != nil {
		h.logger.Error("Failed to update instance", "error", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to update instance",
		})
		return
	}

	h.logger.Info("Instance cancelled", "id", instance.ID, "name", instance.Name)
	c.JSON(http.StatusOK, instance)
}

// GetInstanceSteps handles GET /api/v1/instances/:id/steps
func (h *InstanceHandler) GetInstanceSteps(c *gin.Context) {
	id := c.Param("id")
	instanceID, err := uuid.Parse(id)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid instance ID",
		})
		return
	}

	var steps []models.WorkflowStep
	if err := h.db.Where("instance_id = ?", instanceID).Order("created_at ASC").Find(&steps).Error; err != nil {
		h.logger.Error("Failed to fetch steps", "error", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to fetch steps",
		})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"steps": steps,
	})
}

// TriggerWebhook handles POST /api/v1/triggers/webhook/:template_id
func (h *InstanceHandler) TriggerWebhook(c *gin.Context) {
	templateIDStr := c.Param("template_id")
	templateID, err := uuid.Parse(templateIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid template ID",
		})
		return
	}

	var req models.TriggerWebhookRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid request body",
			"details": err.Error(),
		})
		return
	}

	// Validate template exists and is active
	var template models.WorkflowTemplate
	if err := h.db.Where("id = ? AND is_active = true", templateID).First(&template).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			c.JSON(http.StatusNotFound, gin.H{
				"error": "Template not found or inactive",
			})
			return
		}
		h.logger.Error("Failed to fetch template", "error", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to fetch template",
		})
		return
	}

	// Check if template has webhook trigger
	var trigger models.WorkflowTrigger
	if err := h.db.Where("template_id = ? AND trigger_type = 'webhook' AND is_active = true", templateID).First(&trigger).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			c.JSON(http.StatusNotFound, gin.H{
				"error": "No active webhook trigger found for template",
			})
			return
		}
		h.logger.Error("Failed to fetch trigger", "error", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to fetch trigger",
		})
		return
	}

	// Create workflow instance
	instance := models.WorkflowInstance{
		TemplateID: templateID,
		Name:       template.Name + " (Webhook Triggered)",
		Variables:  req.Variables,
		Context:    req.Context,
		Status:     models.WorkflowStatusPending,
		CreatedBy:  "webhook",
	}

	if instance.Variables == nil {
		instance.Variables = make(models.JSONB)
	}
	if instance.Context == nil {
		instance.Context = make(models.JSONB)
	}

	if err := h.db.Create(&instance).Error; err != nil {
		h.logger.Error("Failed to create instance", "error", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to create instance",
		})
		return
	}

	// Update trigger last triggered time
	now := time.Now()
	trigger.LastTriggeredAt = &now
	h.db.Save(&trigger)

	// Auto-start the instance
	instance.Status = models.WorkflowStatusRunning
	instance.StartedAt = &now
	if err := h.db.Save(&instance).Error; err != nil {
		h.logger.Error("Failed to start instance", "error", err)
	} else {
		// Queue instance for execution
		if err := h.engine.QueueInstance(instance.ID); err != nil {
			h.logger.Error("Failed to queue instance", "error", err, "instance_id", instance.ID)
		}
	}

	h.logger.Info("Webhook triggered instance", "id", instance.ID, "template", template.Name)
	c.JSON(http.StatusCreated, gin.H{
		"instance_id": instance.ID,
		"message":     "Workflow instance created and started",
	})
}