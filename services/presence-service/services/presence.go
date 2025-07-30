package services

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"strings"
	"time"

	"github.com/redis/go-redis/v9"
	"chorus/presence-service/models"
)

const (
	presenceKeyPrefix = "presence:"
	onlineSetKey     = "online_users"
)

type PresenceService struct {
	redis  *redis.Client
	logger *log.Logger
	ttl    time.Duration
}

func NewPresenceService(redisClient *redis.Client, logger *log.Logger) *PresenceService {
	return &PresenceService{
		redis:  redisClient,
		logger: logger,
		ttl:    120 * time.Second, // Default 2 minutes
	}
}

func (ps *PresenceService) SetPresenceTTL(ttl time.Duration) {
	ps.ttl = ttl
}

func (ps *PresenceService) UpdatePresence(ctx context.Context, userID, status, device string) error {
	presence := models.UserPresence{
		UserID:   userID,
		Status:   status,
		LastSeen: time.Now(),
		Device:   device,
	}
	
	data, err := json.Marshal(presence)
	if err != nil {
		return fmt.Errorf("failed to marshal presence data: %w", err)
	}
	
	key := presenceKeyPrefix + userID
	
	// Use pipeline for atomic operations
	pipe := ps.redis.Pipeline()
	
	// Set presence data with TTL
	pipe.Set(ctx, key, data, ps.ttl)
	
	// Add user to online set with TTL
	pipe.SAdd(ctx, onlineSetKey, userID)
	pipe.Expire(ctx, onlineSetKey, ps.ttl*2) // Keep online set alive longer
	
	_, err = pipe.Exec(ctx)
	if err != nil {
		return fmt.Errorf("failed to update presence: %w", err)
	}
	
	ps.logger.Printf("Updated presence for user %s: %s", userID, status)
	return nil
}

func (ps *PresenceService) GetPresence(ctx context.Context, userID string) (*models.UserPresence, error) {
	key := presenceKeyPrefix + userID
	
	data, err := ps.redis.Get(ctx, key).Result()
	if err != nil {
		if err == redis.Nil {
			// User not found or expired, return offline status
			return &models.UserPresence{
				UserID:   userID,
				Status:   "offline",
				LastSeen: time.Time{},
			}, nil
		}
		return nil, fmt.Errorf("failed to get presence: %w", err)
	}
	
	var presence models.UserPresence
	if err := json.Unmarshal([]byte(data), &presence); err != nil {
		return nil, fmt.Errorf("failed to unmarshal presence data: %w", err)
	}
	
	// Check if the presence is still valid based on TTL
	if time.Since(presence.LastSeen) > ps.ttl {
		presence.Status = "offline"
	}
	
	return &presence, nil
}

func (ps *PresenceService) GetOnlineUsers(ctx context.Context) ([]models.UserPresence, error) {
	// Get all user IDs from the online set
	userIDs, err := ps.redis.SMembers(ctx, onlineSetKey).Result()
	if err != nil {
		return nil, fmt.Errorf("failed to get online users: %w", err)
	}
	
	if len(userIDs) == 0 {
		return []models.UserPresence{}, nil
	}
	
	// Build keys for pipeline get
	keys := make([]string, len(userIDs))
	for i, userID := range userIDs {
		keys[i] = presenceKeyPrefix + userID
	}
	
	// Get all presence data in one pipeline
	pipe := ps.redis.Pipeline()
	cmds := make([]*redis.StringCmd, len(keys))
	for i, key := range keys {
		cmds[i] = pipe.Get(ctx, key)
	}
	
	_, err = pipe.Exec(ctx)
	if err != nil && err != redis.Nil {
		return nil, fmt.Errorf("failed to get presence data: %w", err)
	}
	
	var onlineUsers []models.UserPresence
	validUsers := make([]string, 0, len(userIDs))
	
	for i, cmd := range cmds {
		data, err := cmd.Result()
		if err != nil {
			if err == redis.Nil {
				// User presence expired, remove from online set
				continue
			}
			ps.logger.Printf("Error getting presence for user %s: %v", userIDs[i], err)
			continue
		}
		
		var presence models.UserPresence
		if err := json.Unmarshal([]byte(data), &presence); err != nil {
			ps.logger.Printf("Error unmarshaling presence for user %s: %v", userIDs[i], err)
			continue
		}
		
		// Check if still online based on TTL
		if time.Since(presence.LastSeen) <= ps.ttl {
			onlineUsers = append(onlineUsers, presence)
			validUsers = append(validUsers, presence.UserID)
		}
	}
	
	// Clean up online set - remove expired users
	if len(validUsers) != len(userIDs) {
		expiredUsers := make([]string, 0)
		for _, userID := range userIDs {
			found := false
			for _, validUser := range validUsers {
				if userID == validUser {
					found = true
					break
				}
			}
			if !found {
				expiredUsers = append(expiredUsers, userID)
			}
		}
		
		if len(expiredUsers) > 0 {
			ps.redis.SRem(ctx, onlineSetKey, expiredUsers)
		}
	}
	
	return onlineUsers, nil
}

func (ps *PresenceService) RemovePresence(ctx context.Context, userID string) error {
	key := presenceKeyPrefix + userID
	
	pipe := ps.redis.Pipeline()
	pipe.Del(ctx, key)
	pipe.SRem(ctx, onlineSetKey, userID)
	
	_, err := pipe.Exec(ctx)
	if err != nil {
		return fmt.Errorf("failed to remove presence: %w", err)
	}
	
	ps.logger.Printf("Removed presence for user %s", userID)
	return nil
}

func (ps *PresenceService) IsOnline(ctx context.Context, userID string) (bool, error) {
	presence, err := ps.GetPresence(ctx, userID)
	if err != nil {
		return false, err
	}
	
	return presence.Status != "offline" && time.Since(presence.LastSeen) <= ps.ttl, nil
}