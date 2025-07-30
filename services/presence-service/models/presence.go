package models

import "time"

type UserPresence struct {
	UserID    string    `json:"user_id"`
	Status    string    `json:"status"` // online, away, busy, offline
	LastSeen  time.Time `json:"last_seen"`
	Device    string    `json:"device,omitempty"`
}

type HeartbeatRequest struct {
	UserID string `json:"user_id"`
	Status string `json:"status"`
	Device string `json:"device,omitempty"`
}

type StatusResponse struct {
	UserID   string    `json:"user_id"`
	Status   string    `json:"status"`
	LastSeen time.Time `json:"last_seen"`
	IsOnline bool      `json:"is_online"`
}

type OnlineUsersResponse struct {
	Count int            `json:"count"`
	Users []UserPresence `json:"users"`
}