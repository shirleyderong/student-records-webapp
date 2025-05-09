import shutil
import datetime
import os

# Timestamp
timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

# Backup database
db_backup_filename = f"backup_{timestamp}.db"
shutil.copy("database.db", db_backup_filename)
print(f"Database backed up as {db_backup_filename}")

# Backup encryption key
key_backup_filename = f"backup_secret_{timestamp}.key"
shutil.copy("keys/secret.key", key_backup_filename)
print(f"Encryption key backed up as {key_backup_filename}")