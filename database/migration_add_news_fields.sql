-- Migration script to add news fields to existing database
-- Run this on your Supabase database to add the missing news columns

-- Add news fields to players table
ALTER TABLE public.players 
ADD COLUMN IF NOT EXISTS news TEXT,
ADD COLUMN IF NOT EXISTS news_added TIMESTAMP WITH TIME ZONE;

-- Add news field to player_history table (if not exists)
ALTER TABLE public.player_history 
ADD COLUMN IF NOT EXISTS news TEXT;

-- Update the live_monitor_history table to support news tracking
-- Add columns for tracking news changes
ALTER TABLE public.live_monitor_history 
ADD COLUMN IF NOT EXISTS old_news TEXT,
ADD COLUMN IF NOT EXISTS new_news TEXT;

-- Create index on news_added for better query performance
CREATE INDEX IF NOT EXISTS idx_players_news_added ON public.players(news_added);

-- Create index on news field for filtering
CREATE INDEX IF NOT EXISTS idx_players_news ON public.players(news) WHERE news IS NOT NULL AND news != '';

-- Update the updated_at trigger to also update news_added when news changes
CREATE OR REPLACE FUNCTION update_news_added_column()
RETURNS TRIGGER AS $$
BEGIN
    -- Only update news_added if news actually changed
    IF OLD.news IS DISTINCT FROM NEW.news THEN
        NEW.news_added = CURRENT_TIMESTAMP;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for news_added updates
DROP TRIGGER IF EXISTS trigger_update_news_added ON public.players;
CREATE TRIGGER trigger_update_news_added
    BEFORE UPDATE ON public.players
    FOR EACH ROW
    EXECUTE FUNCTION update_news_added_column();

-- Add comments for documentation
COMMENT ON COLUMN public.players.news IS 'Player news/updates from FPL API';
COMMENT ON COLUMN public.players.news_added IS 'Timestamp when news was last updated';
COMMENT ON COLUMN public.player_history.news IS 'Player news at time of snapshot';
COMMENT ON COLUMN public.live_monitor_history.old_news IS 'Previous news value for change tracking';
COMMENT ON COLUMN public.live_monitor_history.new_news IS 'New news value for change tracking';
