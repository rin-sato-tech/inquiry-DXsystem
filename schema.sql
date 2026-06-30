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