CREATE TABLE IF NOT EXISTS inquiries (
    request_id TEXT PRIMARY KEY,
    request_date TEXT NOT NULL,
    request_time TEXT,
    requester TEXT NOT NULL,
    department TEXT NOT NULL,
    channel TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT,
    detail TEXT NOT NULL,
    missing_info TEXT,
    priority TEXT NOT NULL,
    due_date TEXT NOT NULL,
    assignee TEXT,
    status TEXT NOT NULL,
    response_summary TEXT,
    record_issue TEXT,
    completed_date TEXT,
    faq_candidate INTEGER DEFAULT 0,
    faq_title TEXT DEFAULT '',
    faq_answer TEXT DEFAULT '',
    additional_info TEXT DEFAULT '',
    requester_visible INTEGER DEFAULT 1,
    last_status_changed_at TEXT DEFAULT '',
    management_minutes INTEGER DEFAULT 0,
    actual_response_minutes INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_inquiries_request_date
ON inquiries(request_date);

CREATE INDEX IF NOT EXISTS idx_inquiries_due_date
ON inquiries(due_date);

CREATE INDEX IF NOT EXISTS idx_inquiries_status
ON inquiries(status);

CREATE INDEX IF NOT EXISTS idx_inquiries_category
ON inquiries(category);

CREATE INDEX IF NOT EXISTS idx_inquiries_assignee
ON inquiries(assignee);


CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    user_name TEXT NOT NULL,
    department TEXT DEFAULT '',
    email TEXT DEFAULT '',
    role TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (role IN ('requester', 'staff', 'admin', 'viewer')),
    CHECK (is_active IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_users_role
ON users(role);

CREATE INDEX IF NOT EXISTS idx_users_is_active
ON users(is_active);


CREATE TABLE IF NOT EXISTS faq_items (
    faq_id TEXT PRIMARY KEY,
    source_request_id TEXT DEFAULT '',
    category TEXT NOT NULL,
    title TEXT NOT NULL,
    answer TEXT NOT NULL,
    is_public INTEGER DEFAULT 0,
    view_count INTEGER DEFAULT 0,
    helpful_count INTEGER DEFAULT 0,
    created_by TEXT DEFAULT '',
    updated_by TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (is_public IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_faq_items_category
ON faq_items(category);

CREATE INDEX IF NOT EXISTS idx_faq_items_is_public
ON faq_items(is_public);

CREATE INDEX IF NOT EXISTS idx_faq_items_source_request_id
ON faq_items(source_request_id);


CREATE TABLE IF NOT EXISTS inquiry_comments (
    comment_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL,
    comment_body TEXT NOT NULL,
    visibility TEXT DEFAULT 'internal',
    created_by TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    CHECK (visibility IN ('internal', 'requester'))
);

CREATE INDEX IF NOT EXISTS idx_inquiry_comments_request_id
ON inquiry_comments(request_id);

CREATE INDEX IF NOT EXISTS idx_inquiry_comments_created_at
ON inquiry_comments(created_at);


CREATE TABLE IF NOT EXISTS status_history (
    history_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL,
    old_status TEXT DEFAULT '',
    new_status TEXT NOT NULL,
    changed_by TEXT DEFAULT '',
    changed_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_status_history_request_id
ON status_history(request_id);

CREATE INDEX IF NOT EXISTS idx_status_history_changed_at
ON status_history(changed_at);


CREATE TABLE IF NOT EXISTS operation_logs (
    log_id TEXT PRIMARY KEY,
    user_id TEXT DEFAULT '',
    action TEXT NOT NULL,
    target_table TEXT NOT NULL,
    target_id TEXT NOT NULL,
    detail TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_operation_logs_user_id
ON operation_logs(user_id);

CREATE INDEX IF NOT EXISTS idx_operation_logs_action
ON operation_logs(action);

CREATE INDEX IF NOT EXISTS idx_operation_logs_target_id
ON operation_logs(target_id);

CREATE INDEX IF NOT EXISTS idx_operation_logs_created_at
ON operation_logs(created_at);


CREATE TABLE IF NOT EXISTS notification_logs (
    notification_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL,
    notification_type TEXT NOT NULL,
    recipient_user_id TEXT DEFAULT '',
    message TEXT NOT NULL,
    status TEXT DEFAULT 'created',
    created_at TEXT NOT NULL,
    CHECK (
        notification_type IN (
            'before_due',
            'overdue',
            'unassigned',
            'waiting_too_long',
            'status_changed',
            'completed'
        )
    ),
    CHECK (status IN ('created', 'reviewed', 'skipped', 'sent'))
);

CREATE INDEX IF NOT EXISTS idx_notification_logs_request_id
ON notification_logs(request_id);

CREATE INDEX IF NOT EXISTS idx_notification_logs_notification_type
ON notification_logs(notification_type);

CREATE INDEX IF NOT EXISTS idx_notification_logs_created_at
ON notification_logs(created_at);