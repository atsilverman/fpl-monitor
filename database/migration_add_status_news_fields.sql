-- Migration to add status and news fields to user_notifications table
-- This supports the new status change notification feature

-- Add new columns to user_notifications table
ALTER TABLE public.user_notifications 
ADD COLUMN player_status TEXT,
ADD COLUMN old_status TEXT,
ADD COLUMN news_text TEXT,
ADD COLUMN old_news TEXT;

-- Add comments for documentation
COMMENT ON COLUMN public.user_notifications.player_status IS 'Current player status (a, d, i, s, u, n)';
COMMENT ON COLUMN public.user_notifications.old_status IS 'Previous player status for status change notifications';
COMMENT ON COLUMN public.user_notifications.news_text IS 'Current news text for the player';
COMMENT ON COLUMN public.user_notifications.old_news IS 'Previous news text for news change notifications';

-- Add index for status-based queries
CREATE INDEX IF NOT EXISTS idx_user_notifications_player_status ON public.user_notifications(player_status);
CREATE INDEX IF NOT EXISTS idx_user_notifications_notification_type ON public.user_notifications(notification_type);
