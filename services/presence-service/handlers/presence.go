package handlers

import (
	"encoding/json"
	"log"
	"net/http"

	"chorus/presence-service/models"
	"chorus/presence-service/services"
)

type PresenceHandler struct {
	service *services.PresenceService
	logger  *log.Logger
}

func NewPresenceHandler(service *services.PresenceService, logger *log.Logger) *PresenceHandler {
	return &PresenceHandler{
		service: service,
		logger:  logger,
	}
}

func (ph *PresenceHandler) Heartbeat(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req models.HeartbeatRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid JSON payload", http.StatusBadRequest)
		return
	}

	if req.UserID == "" {
		http.Error(w, "user_id is required", http.StatusBadRequest)
		return
	}

	if req.Status == "" {
		req.Status = "online"
	}

	err := ph.service.UpdatePresence(r.Context(), req.UserID, req.Status, req.Device)
	if err != nil {
		ph.logger.Printf("Failed to update presence: %v", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]string{
		"status": "success",
		"message": "Presence updated",
	})
}

func (ph *PresenceHandler) GetStatus(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	userID := r.URL.Query().Get("user_id")
	if userID == "" {
		http.Error(w, "user_id parameter is required", http.StatusBadRequest)
		return
	}

	presence, err := ph.service.GetPresence(r.Context(), userID)
	if err != nil {
		ph.logger.Printf("Failed to get presence: %v", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	isOnline, _ := ph.service.IsOnline(r.Context(), userID)

	response := models.StatusResponse{
		UserID:   presence.UserID,
		Status:   presence.Status,
		LastSeen: presence.LastSeen,
		IsOnline: isOnline,
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(response)
}

func (ph *PresenceHandler) GetOnlineUsers(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	users, err := ph.service.GetOnlineUsers(r.Context())
	if err != nil {
		ph.logger.Printf("Failed to get online users: %v", err)
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	response := models.OnlineUsersResponse{
		Count: len(users),
		Users: users,
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(response)
}