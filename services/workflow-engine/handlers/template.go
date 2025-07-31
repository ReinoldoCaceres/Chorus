package handlers

import (
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"gorm.io/gorm"

	"chorus/workflow-engine/models"
	"chorus/workflow-engine/utils"
)

type TemplateHandler struct {
	db     *gorm.DB
	logger *utils.Logger
}

func NewTemplateHandler(db *gorm.DB, logger *utils.Logger) *TemplateHandler {
	return &TemplateHandler{
		db:     db,
		logger: logger,
	}
}

// ListTemplates handles GET /api/v1/templates
func (h *TemplateHandler) ListTemplates(c *gin.Context) {
	// Parse query parameters
	page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
	pageSize, _ := strconv.Atoi(c.DefaultQuery("page_size", "20"))
	category := c.Query("category")
	isActive := c.Query("is_active")

	if page < 1 {
		page = 1
	}
	if pageSize < 1 || pageSize > 100 {
		pageSize = 20
	}

	// Build query
	query := h.db.Model(&models.WorkflowTemplate{})

	if category != "" {
		query = query.Where("category = ?", category)
	}

	if isActive != "" {
		if isActive == "true" {
			query = query.Where("is_active = true")
		} else if isActive == "false" {
			query = query.Where("is_active = false")
		}
	}

	// Get total count
	var total int64
	if err := query.Count(&total).Error; err != nil {
		h.logger.Error("Failed to count templates", "error", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to count templates",
		})
		return
	}

	// Get templates with pagination
	var templates []models.WorkflowTemplate
	offset := (page - 1) * pageSize
	if err := query.Offset(offset).Limit(pageSize).Order("created_at DESC").Find(&templates).Error; err != nil {
		h.logger.Error("Failed to fetch templates", "error", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to fetch templates",
		})
		return
	}

	totalPages := int((total + int64(pageSize) - 1) / int64(pageSize))

	response := models.ListResponse[models.WorkflowTemplate]{
		Data:       templates,
		Total:      total,
		Page:       page,
		PageSize:   pageSize,
		TotalPages: totalPages,
	}

	c.JSON(http.StatusOK, response)
}

// CreateTemplate handles POST /api/v1/templates
func (h *TemplateHandler) CreateTemplate(c *gin.Context) {
	var req models.CreateTemplateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid request body",
			"details": err.Error(),
		})
		return
	}

	// Get user ID from context
	userID, _ := c.Get("userID")

	template := models.WorkflowTemplate{
		Name:        req.Name,
		Description: req.Description,
		Category:    req.Category,
		Version:     req.Version,
		Schema:      req.Schema,
		Metadata:    req.Metadata,
		CreatedBy:   userID.(string),
	}

	if template.Version == "" {
		template.Version = "1.0.0"
	}
	if template.Metadata == nil {
		template.Metadata = make(models.JSONB)
	}

	// Validate workflow schema
	if err := h.validateWorkflowSchema(template.Schema); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid workflow schema",
			"details": err.Error(),
		})
		return
	}

	if err := h.db.Create(&template).Error; err != nil {
		h.logger.Error("Failed to create template", "error", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to create template",
		})
		return
	}

	h.logger.Info("Template created", "id", template.ID, "name", template.Name)
	c.JSON(http.StatusCreated, template)
}

// GetTemplate handles GET /api/v1/templates/:id
func (h *TemplateHandler) GetTemplate(c *gin.Context) {
	id := c.Param("id")
	templateID, err := uuid.Parse(id)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid template ID",
		})
		return
	}

	var template models.WorkflowTemplate
	if err := h.db.First(&template, templateID).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			c.JSON(http.StatusNotFound, gin.H{
				"error": "Template not found",
			})
			return
		}
		h.logger.Error("Failed to fetch template", "error", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to fetch template",
		})
		return
	}

	c.JSON(http.StatusOK, template)
}

// UpdateTemplate handles PUT /api/v1/templates/:id
func (h *TemplateHandler) UpdateTemplate(c *gin.Context) {
	id := c.Param("id")
	templateID, err := uuid.Parse(id)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid template ID",
		})
		return
	}

	var req models.UpdateTemplateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid request body",
			"details": err.Error(),
		})
		return
	}

	var template models.WorkflowTemplate
	if err := h.db.First(&template, templateID).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			c.JSON(http.StatusNotFound, gin.H{
				"error": "Template not found",
			})
			return
		}
		h.logger.Error("Failed to fetch template", "error", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to fetch template",
		})
		return
	}

	// Update fields if provided
	if req.Name != nil {
		template.Name = *req.Name
	}
	if req.Description != nil {
		template.Description = *req.Description
	}
	if req.Category != nil {
		template.Category = *req.Category
	}
	if req.Schema != nil {
		if err := h.validateWorkflowSchema(*req.Schema); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"error": "Invalid workflow schema",
				"details": err.Error(),
			})
			return
		}
		template.Schema = *req.Schema
	}
	if req.Metadata != nil {
		template.Metadata = *req.Metadata
	}
	if req.IsActive != nil {
		template.IsActive = *req.IsActive
	}

	if err := h.db.Save(&template).Error; err != nil {
		h.logger.Error("Failed to update template", "error", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to update template",
		})
		return
	}

	h.logger.Info("Template updated", "id", template.ID, "name", template.Name)
	c.JSON(http.StatusOK, template)
}

// DeleteTemplate handles DELETE /api/v1/templates/:id
func (h *TemplateHandler) DeleteTemplate(c *gin.Context) {
	id := c.Param("id")
	templateID, err := uuid.Parse(id)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid template ID",
		})
		return
	}

	// Check if template exists
	var template models.WorkflowTemplate
	if err := h.db.First(&template, templateID).Error; err != nil {
		if err == gorm.ErrRecordNotFound {
			c.JSON(http.StatusNotFound, gin.H{
				"error": "Template not found",
			})
			return
		}
		h.logger.Error("Failed to fetch template", "error", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to fetch template",
		})
		return
	}

	// Check if template has active instances
	var instanceCount int64
	if err := h.db.Model(&models.WorkflowInstance{}).Where("template_id = ? AND status IN ?", templateID, []string{"pending", "running", "paused"}).Count(&instanceCount).Error; err != nil {
		h.logger.Error("Failed to check active instances", "error", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to check active instances",
		})
		return
	}

	if instanceCount > 0 {
		c.JSON(http.StatusConflict, gin.H{
			"error": "Cannot delete template with active instances",
		})
		return
	}

	// Soft delete by setting is_active to false instead of hard delete
	template.IsActive = false
	if err := h.db.Save(&template).Error; err != nil {
		h.logger.Error("Failed to delete template", "error", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to delete template",
		})
		return
	}

	h.logger.Info("Template deleted", "id", template.ID, "name", template.Name)
	c.JSON(http.StatusOK, gin.H{
		"message": "Template deleted successfully",
	})
}

// validateWorkflowSchema validates the workflow schema structure
func (h *TemplateHandler) validateWorkflowSchema(schema models.JSONB) error {
	// Basic schema validation - in a real implementation, you might want more sophisticated validation
	if schema == nil {
		return nil
	}

	steps, ok := schema["steps"]
	if !ok {
		return nil // Steps are optional in some cases
	}

	stepsSlice, ok := steps.([]interface{})
	if !ok {
		return nil
	}

	// Validate each step has required fields
	for _, step := range stepsSlice {
		stepMap, ok := step.(map[string]interface{})
		if !ok {
			continue
		}

		// Check required fields
		if _, ok := stepMap["id"]; !ok {
			return nil
		}
		if _, ok := stepMap["type"]; !ok {
			return nil
		}
	}

	return nil
}