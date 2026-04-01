from supabase import create_client, Client
from app.core.config import settings

# Use credentials from settings:
SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_KEY = settings.SUPABASE_KEY

# Initialize the Supabase client acting as service role
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
