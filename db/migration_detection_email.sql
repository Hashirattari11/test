-- Detection confirmation email: one-time email after first scan with new detections.
-- Apply in Supabase SQL editor.

alter table repos add column if not exists detection_email_sent boolean default false;
