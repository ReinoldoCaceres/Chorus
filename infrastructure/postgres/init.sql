-- Chorus Platform Database Schema
-- Version 1.0.0

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS workflow;
CREATE SCHEMA IF NOT EXISTS monitoring;
CREATE SCHEMA IF NOT EXISTS agent;
CREATE SCHEMA IF NOT EXISTS notification;

-- Set search path
SET search_path TO public, workflow, monitoring, agent, notification;

-- =====================================================
-- WORKFLOW SCHEMA
-- =====================================================

-- Workflow Templates table
CREATE TABLE workflow.templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    version VARCHAR(50) DEFAULT '1.0.0',
    schema JSONB NOT NULL,
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    CONSTRAINT unique_template_name_version UNIQUE (name, version)
);

-- Workflow Instances table
CREATE TABLE workflow.instances (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id UUID NOT NULL REFERENCES workflow.templates(id),
    name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    context JSONB DEFAULT '{}',
    variables JSONB DEFAULT '{}',
    current_step VARCHAR(255),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    CONSTRAINT check_status CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled', 'paused'))
);

-- Workflow Steps table
CREATE TABLE workflow.steps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    instance_id UUID NOT NULL REFERENCES workflow.instances(id) ON DELETE CASCADE,
    step_id VARCHAR(255) NOT NULL,
    step_type VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    input_data JSONB DEFAULT '{}',
    output_data JSONB DEFAULT '{}',
    error_data JSONB,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_step_status CHECK (status IN ('pending', 'running', 'completed', 'failed', 'skipped'))
);

-- Workflow Triggers table
CREATE TABLE workflow.triggers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id UUID NOT NULL REFERENCES workflow.templates(id),
    trigger_type VARCHAR(50) NOT NULL,
    trigger_config JSONB NOT NULL,
    is_active BOOLEAN DEFAULT true,
    last_triggered_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_trigger_type CHECK (trigger_type IN ('manual', 'schedule', 'event', 'webhook', 'condition'))
);

-- =====================================================
-- MONITORING SCHEMA
-- =====================================================

-- System Metrics table
CREATE TABLE monitoring.system_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hostname VARCHAR(255) NOT NULL,
    metric_type VARCHAR(100) NOT NULL,
    metric_value NUMERIC NOT NULL,
    metric_unit VARCHAR(50),
    tags JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Process Metrics table
CREATE TABLE monitoring.process_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    process_id INTEGER NOT NULL,
    process_name VARCHAR(255) NOT NULL,
    hostname VARCHAR(255) NOT NULL,
    cpu_percent NUMERIC(5,2),
    memory_mb NUMERIC,
    memory_percent NUMERIC(5,2),
    disk_read_bytes BIGINT,
    disk_write_bytes BIGINT,
    network_sent_bytes BIGINT,
    network_recv_bytes BIGINT,
    status VARCHAR(50),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Alerts table
CREATE TABLE monitoring.alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_type VARCHAR(100) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    source VARCHAR(255) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    alert_metadata JSONB DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'active',
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    acknowledged_by VARCHAR(255),
    resolved_at TIMESTAMP WITH TIME ZONE,
    resolved_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_severity CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info')),
    CONSTRAINT check_alert_status CHECK (status IN ('active', 'acknowledged', 'resolved', 'suppressed'))
);

-- Alert Rules table
CREATE TABLE monitoring.alert_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    rule_type VARCHAR(100) NOT NULL,
    condition JSONB NOT NULL,
    severity VARCHAR(50) NOT NULL,
    notification_channels JSONB DEFAULT '[]',
    cooldown_minutes INTEGER DEFAULT 5,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_rule_severity CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info'))
);

-- =====================================================
-- AGENT SCHEMA
-- =====================================================

-- Agent Tasks table
CREATE TABLE agent.tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_type VARCHAR(100) NOT NULL,
    priority INTEGER DEFAULT 5,
    payload JSONB NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    assigned_agent VARCHAR(255),
    result JSONB,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    scheduled_at TIMESTAMP WITH TIME ZONE,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_priority CHECK (priority BETWEEN 1 AND 10),
    CONSTRAINT check_task_status CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled'))
);

-- Agent Knowledge Base table
CREATE TABLE agent.knowledge_base (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    embedding_id VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    tags TEXT[],
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255)
);

-- Agent Conversations table
CREATE TABLE agent.conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255),
    message_type VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    context JSONB DEFAULT '{}',
    parent_message_id UUID,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_message_type CHECK (message_type IN ('user', 'agent', 'system'))
);

-- =====================================================
-- NOTIFICATION SCHEMA
-- =====================================================

-- Notification Templates table
CREATE TABLE notification.templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    channel VARCHAR(50) NOT NULL,
    subject VARCHAR(255),
    body_template TEXT NOT NULL,
    variables JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_channel CHECK (channel IN ('email', 'sms', 'webhook', 'slack', 'teams'))
);

-- Notifications table
CREATE TABLE notification.notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id UUID REFERENCES notification.templates(id),
    recipient VARCHAR(255) NOT NULL,
    channel VARCHAR(50) NOT NULL,
    subject VARCHAR(255),
    body TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    metadata JSONB DEFAULT '{}',
    scheduled_at TIMESTAMP WITH TIME ZONE,
    sent_at TIMESTAMP WITH TIME ZONE,
    failed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_notification_status CHECK (status IN ('pending', 'sent', 'failed', 'cancelled')),
    CONSTRAINT check_notification_channel CHECK (channel IN ('email', 'sms', 'webhook', 'slack', 'teams'))
);

-- Notification Subscriptions table
CREATE TABLE notification.subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255) NOT NULL,
    channel VARCHAR(50) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    config JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_user_channel_event UNIQUE (user_id, channel, event_type)
);

-- =====================================================
-- PUBLIC SCHEMA TABLES
-- =====================================================

-- Users table (simplified for development)
CREATE TABLE public.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'user',
    is_active BOOLEAN DEFAULT true,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_role CHECK (role IN ('admin', 'user', 'viewer'))
);

-- Audit Log table
CREATE TABLE public.audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id VARCHAR(255),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    changes JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- INDEXES
-- =====================================================

-- Workflow indexes
CREATE INDEX idx_workflow_instances_template_id ON workflow.instances(template_id);
CREATE INDEX idx_workflow_instances_status ON workflow.instances(status);
CREATE INDEX idx_workflow_instances_created_at ON workflow.instances(created_at DESC);
CREATE INDEX idx_workflow_steps_instance_id ON workflow.steps(instance_id);
CREATE INDEX idx_workflow_steps_status ON workflow.steps(status);
CREATE INDEX idx_workflow_triggers_template_id ON workflow.triggers(template_id);
CREATE INDEX idx_workflow_triggers_active ON workflow.triggers(is_active) WHERE is_active = true;

-- Monitoring indexes
CREATE INDEX idx_system_metrics_timestamp ON monitoring.system_metrics(timestamp DESC);
CREATE INDEX idx_system_metrics_hostname_type ON monitoring.system_metrics(hostname, metric_type);
CREATE INDEX idx_process_metrics_timestamp ON monitoring.process_metrics(timestamp DESC);
CREATE INDEX idx_process_metrics_hostname ON monitoring.process_metrics(hostname);
CREATE INDEX idx_alerts_status ON monitoring.alerts(status) WHERE status = 'active';
CREATE INDEX idx_alerts_created_at ON monitoring.alerts(created_at DESC);
CREATE INDEX idx_alert_rules_active ON monitoring.alert_rules(is_active) WHERE is_active = true;

-- Agent indexes
CREATE INDEX idx_agent_tasks_status ON agent.tasks(status);
CREATE INDEX idx_agent_tasks_scheduled ON agent.tasks(scheduled_at) WHERE status = 'pending';
CREATE INDEX idx_knowledge_base_category ON agent.knowledge_base(category);
CREATE INDEX idx_knowledge_base_tags ON agent.knowledge_base USING GIN(tags);
CREATE INDEX idx_conversations_session ON agent.conversations(session_id);
CREATE INDEX idx_conversations_created_at ON agent.conversations(created_at DESC);

-- Notification indexes
CREATE INDEX idx_notifications_status ON notification.notifications(status);
CREATE INDEX idx_notifications_scheduled ON notification.notifications(scheduled_at) WHERE status = 'pending';
CREATE INDEX idx_notifications_recipient ON notification.notifications(recipient);
CREATE INDEX idx_subscriptions_user ON notification.subscriptions(user_id);
CREATE INDEX idx_subscriptions_active ON notification.subscriptions(is_active) WHERE is_active = true;

-- Audit log indexes
CREATE INDEX idx_audit_log_created_at ON public.audit_log(created_at DESC);
CREATE INDEX idx_audit_log_user_id ON public.audit_log(user_id);
CREATE INDEX idx_audit_log_resource ON public.audit_log(resource_type, resource_id);

-- =====================================================
-- FUNCTIONS AND TRIGGERS
-- =====================================================

-- Update timestamp function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply update timestamp triggers
CREATE TRIGGER update_workflow_templates_updated_at BEFORE UPDATE ON workflow.templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_workflow_instances_updated_at BEFORE UPDATE ON workflow.instances
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_workflow_steps_updated_at BEFORE UPDATE ON workflow.steps
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_workflow_triggers_updated_at BEFORE UPDATE ON workflow.triggers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_alerts_updated_at BEFORE UPDATE ON monitoring.alerts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_alert_rules_updated_at BEFORE UPDATE ON monitoring.alert_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_agent_tasks_updated_at BEFORE UPDATE ON agent.tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_knowledge_base_updated_at BEFORE UPDATE ON agent.knowledge_base
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_notification_templates_updated_at BEFORE UPDATE ON notification.templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_notifications_updated_at BEFORE UPDATE ON notification.notifications
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON notification.subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- INITIAL DATA
-- =====================================================

-- Insert default admin user
INSERT INTO public.users (username, email, full_name, role) 
VALUES ('admin', 'admin@chorus.local', 'System Administrator', 'admin');

-- Insert sample workflow template
INSERT INTO workflow.templates (name, description, category, schema) 
VALUES (
    'Hello World Workflow',
    'A simple workflow for testing',
    'examples',
    '{
        "steps": [
            {
                "id": "start",
                "type": "start",
                "next": "hello"
            },
            {
                "id": "hello",
                "type": "action",
                "action": "log",
                "params": {
                    "message": "Hello, World!"
                },
                "next": "end"
            },
            {
                "id": "end",
                "type": "end"
            }
        ]
    }'::jsonb
);

-- Insert sample notification template
INSERT INTO notification.templates (name, channel, subject, body_template, variables)
VALUES (
    'welcome_email',
    'email',
    'Welcome to Chorus Platform',
    'Hello {{name}},\n\nWelcome to Chorus Platform! We are excited to have you on board.\n\nBest regards,\nThe Chorus Team',
    '["name"]'::jsonb
);

-- Grant permissions to chorus user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO chorus;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA workflow TO chorus;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA monitoring TO chorus;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA agent TO chorus;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA notification TO chorus;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO chorus;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA workflow TO chorus;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA monitoring TO chorus;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA agent TO chorus;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA notification TO chorus;
GRANT USAGE ON SCHEMA public TO chorus;
GRANT USAGE ON SCHEMA workflow TO chorus;
GRANT USAGE ON SCHEMA monitoring TO chorus;
GRANT USAGE ON SCHEMA agent TO chorus;
GRANT USAGE ON SCHEMA notification TO chorus;