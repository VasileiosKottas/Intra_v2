# fix_calendly_tables.py
"""
Fixed migration script to create the complete Calendly tables schema
Run this to fix the missing columns issue
"""

import sqlite3
import os

def fix_calendly_tables():
    """Fix the Calendly tables to match the model schema"""
    
    # Find the database file
    db_path = None
    possible_paths = [
        'instance/sales_dashboard.db',
        'sales_dashboard.db', 
        'app.db',
        'database.db'
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        print("❌ Database file not found.")
        print("Please specify your database path:")
        db_path = input("Enter database path: ")
    
    print(f"🗄️ Using database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # First, check if tables exist and drop them to recreate with correct schema
        print("🔄 Dropping existing incomplete tables...")
        cursor.execute("DROP TABLE IF EXISTS calendly_events;")
        cursor.execute("DROP TABLE IF EXISTS calendly_sync_logs;")
        
        # Create calendly_events table with COMPLETE schema
        print("🔄 Creating complete calendly_events table...")
        calendly_events_sql = """
        CREATE TABLE calendly_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            calendly_event_id VARCHAR(255) UNIQUE NOT NULL,
            calendly_uri VARCHAR(500) NOT NULL,
            name VARCHAR(255),
            status VARCHAR(50),
            start_time DATETIME NOT NULL,
            end_time DATETIME NOT NULL,
            location_type VARCHAR(100),
            location_value TEXT,
            meeting_notes_plain TEXT,
            meeting_notes_html TEXT,
            event_type_name VARCHAR(255),
            event_type_uri VARCHAR(500),
            event_type_duration INTEGER,
            host_name VARCHAR(255),
            host_email VARCHAR(255),
            host_uri VARCHAR(500),
            guests_data JSON,
            guest_count INTEGER DEFAULT 0,
            created_at_calendly DATETIME,
            updated_at_calendly DATETIME,
            cancel_url VARCHAR(500),
            reschedule_url VARCHAR(500),
            raw_data JSON,
            last_synced DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
        cursor.execute(calendly_events_sql)
        
        # Create calendly_sync_logs table with COMPLETE schema
        print("🔄 Creating complete calendly_sync_logs table...")
        calendly_sync_logs_sql = """
        CREATE TABLE calendly_sync_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sync_type VARCHAR(50) NOT NULL,
            start_date DATETIME NOT NULL,
            end_date DATETIME NOT NULL,
            events_fetched INTEGER DEFAULT 0,
            events_created INTEGER DEFAULT 0,
            events_updated INTEGER DEFAULT 0,
            events_skipped INTEGER DEFAULT 0,
            status VARCHAR(20) DEFAULT 'running',
            started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed_at DATETIME,
            duration_seconds FLOAT,
            error_message TEXT,
            api_calls_made INTEGER DEFAULT 0,
            user_email VARCHAR(255),
            team_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
        cursor.execute(calendly_sync_logs_sql)
        
        # Create all necessary indexes
        print("🔄 Creating indexes...")
        indexes = [
            "CREATE INDEX idx_calendly_events_id ON calendly_events(calendly_event_id);",
            "CREATE INDEX idx_calendly_events_start_time ON calendly_events(start_time);",
            "CREATE INDEX idx_calendly_events_status ON calendly_events(status);",
            "CREATE INDEX idx_calendly_events_host_email ON calendly_events(host_email);",
            "CREATE INDEX idx_calendly_events_host_name ON calendly_events(host_name);",
            "CREATE INDEX idx_calendly_events_last_synced ON calendly_events(last_synced);",
            "CREATE INDEX idx_calendly_sync_logs_start_date ON calendly_sync_logs(start_date);",
            "CREATE INDEX idx_calendly_sync_logs_end_date ON calendly_sync_logs(end_date);",
            "CREATE INDEX idx_calendly_sync_logs_user_email ON calendly_sync_logs(user_email);",
            "CREATE INDEX idx_calendly_sync_logs_team_id ON calendly_sync_logs(team_id);"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        conn.commit()
        
        # Verify the tables were created correctly
        print("🔍 Verifying table structure...")
        cursor.execute("PRAGMA table_info(calendly_events);")
        columns = [row[1] for row in cursor.fetchall()]
        
        expected_columns = [
            'id', 'calendly_event_id', 'calendly_uri', 'name', 'status', 
            'start_time', 'end_time', 'location_type', 'location_value',
            'meeting_notes_plain', 'meeting_notes_html', 'event_type_name',
            'event_type_uri', 'event_type_duration', 'host_name', 'host_email',
            'host_uri', 'guests_data', 'guest_count', 'created_at_calendly',
            'updated_at_calendly', 'cancel_url', 'reschedule_url', 'raw_data',
            'last_synced', 'created_at'
        ]
        
        missing_columns = set(expected_columns) - set(columns)
        if missing_columns:
            print(f"⚠️ Warning: Missing columns: {missing_columns}")
        else:
            print("✅ All columns created successfully!")
        
        print(f"📊 Created columns: {columns}")
        
        conn.close()
        
        print("\n✅ Calendly cache tables fixed successfully!")
        print("\n📋 Next steps:")
        print("1. Restart your Flask app")
        print("2. Test the cache endpoints")
        print("3. The cache should now work without column errors")
        
        return True
        
    except Exception as e:
        print(f"❌ Error fixing tables: {e}")
        if 'conn' in locals():
            conn.close()
        return False

def test_table_structure():
    """Test that the table structure matches the model"""
    db_path = None
    possible_paths = [
        'instance/sales_dashboard.db',
        'sales_dashboard.db', 
        'app.db',
        'database.db'
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        print("❌ Database file not found for testing.")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Test calendly_events table
        cursor.execute("PRAGMA table_info(calendly_events);")
        events_columns = cursor.fetchall()
        
        # Test calendly_sync_logs table  
        cursor.execute("PRAGMA table_info(calendly_sync_logs);")
        logs_columns = cursor.fetchall()
        
        print("\n🔍 Table Structure Verification:")
        print(f"📅 calendly_events has {len(events_columns)} columns")
        print(f"📋 calendly_sync_logs has {len(logs_columns)} columns")
        
        print("\n📅 calendly_events columns:")
        for col in events_columns:
            print(f"  - {col[1]} ({col[2]})")
        
        print("\n📋 calendly_sync_logs columns:")
        for col in logs_columns:
            print(f"  - {col[1]} ({col[2]})")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error testing structure: {e}")

if __name__ == "__main__":
    print("🔧 Fixing Calendly cache table schema...")
    success = fix_calendly_tables()
    
    if success:
        print("\n🧪 Testing table structure...")
        test_table_structure()
        print("\n🎉 Migration complete! Your cache should now work properly.")
    else:
        print("\n💥 Migration failed!")