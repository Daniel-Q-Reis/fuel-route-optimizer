#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Django Master Template...${NC}"

# Wait for database to be ready
echo -e "${YELLOW}⏳ Waiting for database...${NC}"
while ! nc -z db 5432; do
  sleep 0.1
done
echo -e "${GREEN}✅ Database is ready!${NC}"

# Wait for Redis to be ready
echo -e "${YELLOW}⏳ Waiting for Redis...${NC}"
while ! nc -z redis 6379; do
  sleep 0.1
done
echo -e "${GREEN}✅ Redis is ready!${NC}"

# Change to app directory
cd /usr/src/app

# Run database migrations
echo -e "${YELLOW}📊 Running database migrations...${NC}"
python manage.py migrate --noinput

# Collect static files
echo -e "${YELLOW}📁 Collecting static files...${NC}"
python manage.py collectstatic --noinput

# Create superuser if it doesn't exist (for development)
if [ "$ENVIRONMENT" = "development" ] || [ "$DEBUG" = "True" ]; then
  echo -e "${YELLOW}👤 Creating superuser (if not exists)...${NC}"
  python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@localhost', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
"
fi

# Create cache table if using database cache
echo -e "${YELLOW}🗄️ Creating cache table...${NC}"
python manage.py createcachetable || echo "Cache table already exists or not needed"

# Load initial data (if exists)
if [ -f "fixtures/initial_data.json" ]; then
  echo -e "${YELLOW}📋 Loading initial data...${NC}"
  python manage.py loaddata fixtures/initial_data.json
fi

echo -e "${GREEN}✨ Django setup completed successfully!${NC}"

# Execute the command passed to the script
exec "$@"
