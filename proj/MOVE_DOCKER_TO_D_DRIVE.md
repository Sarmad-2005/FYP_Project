# Moving Docker from C: to D: Drive

## What are the leftover 8GB?

The 8.21GB remaining is likely:
- **6 Docker images** (the old individual service images still present)
- **Base images** (python:3.11-slim, etc.)
- **Docker system files** (containers, volumes, etc.)

## Step-by-Step: Move Docker to D: Drive

### Option 1: Change Docker Data Directory (Recommended - No Reinstall)

This moves Docker's data without reinstalling:

1. **Stop Docker Desktop**
   - Right-click Docker Desktop icon in system tray → Quit Docker Desktop

2. **Create new directory on D:**
   ```powershell
   mkdir D:\DockerData
   ```

3. **Move Docker data** (if Docker Desktop is installed):
   - Open Docker Desktop Settings
   - Go to "Resources" → "Advanced"
   - Change "Disk image location" to `D:\DockerData`
   - Click "Apply & Restart"

   OR manually via WSL2 (if using WSL2 backend):
   ```powershell
   # Export WSL distribution
   wsl --export docker-desktop-data D:\DockerData\docker-desktop-data.tar
   
   # Unregister old distribution
   wsl --unregister docker-desktop-data
   
   # Import to new location
   wsl --import docker-desktop-data D:\DockerData\docker-desktop-data D:\DockerData\docker-desktop-data.tar --version 2
   
   # Clean up tar file
   del D:\DockerData\docker-desktop-data.tar
   ```

### Option 2: Uninstall and Reinstall Docker Desktop to D:

1. **Export your current images** (optional - to save them):
   ```powershell
   cd d:\PROJ.AI\proj
   docker save proj-api-gateway:latest -o D:\docker-backup\api-gateway.tar
   # Repeat for other images if needed
   ```

2. **Uninstall Docker Desktop**
   - Settings → Apps → Docker Desktop → Uninstall

3. **Download Docker Desktop** from docker.com

4. **Install to D:**
   - Run installer
   - Choose "Custom installation" if available
   - Set installation path to `D:\Program Files\Docker\` (or similar)

5. **Configure data directory during first run:**
   - Open Docker Desktop Settings
   - Resources → Advanced
   - Set "Disk image location" to `D:\DockerData`

6. **Restore images** (if you exported them):
   ```powershell
   docker load -i D:\docker-backup\api-gateway.tar
   ```

### Option 3: Use Docker Engine (Linux-style) on Windows

If you're using WSL2, you can install Docker Engine directly in WSL2 and configure it to use D: drive.

## After Moving Docker

1. **Remove old images:**
   ```powershell
   cd d:\PROJ.AI\proj
   docker-compose down
   docker rmi proj-api-gateway proj-financial-service proj-performance-service proj-csv-analysis-service proj-a2a-router-service proj-scheduler-service -f
   ```

2. **Build new single image:**
   ```powershell
   docker-compose build
   ```

3. **Start services:**
   ```powershell
   docker-compose up -d
   ```

## Verify Docker Location

After moving, verify Docker is using D: drive:
```powershell
docker info | findstr "Docker Root Dir"
```

Or check Docker Desktop Settings → Resources → Advanced

## Expected Space Savings

- **Before:** ~8GB on C: drive
- **After:** All Docker data on D: drive
- **New single image:** ~12.63GB (on D: drive, not C:)
