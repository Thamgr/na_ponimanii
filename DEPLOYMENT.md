# Deployment Guide for Na Ponimanii Bot

This guide explains how to deploy the Na Ponimanii bot and server as systemd services on a Linux server.

## Prerequisites

- A Linux server with systemd (Ubuntu, Debian, CentOS, etc.)
- Python 3.8 or higher
- pip3
- Git (optional, for cloning the repository)

## Files

The deployment package includes the following files:

- `na_ponimanii_bot.service`: Systemd service file for the Telegram bot
- `na_ponimanii_server.service`: Systemd service file for the FastAPI server
- `deploy.sh`: Script to install and start the services
- `uninstall.sh`: Script to remove the services
- `status.sh`: Script to check the status of the services
- `restart.sh`: Script to restart both services
- `update.sh`: Script to pull the latest updates from GitHub and restart services
- `setup_cron_update.sh`: Script to set up automatic updates via cron
- `DEPLOYMENT.md`: This deployment guide

## Deployment Steps

1. Clone or copy the project to your server:
   ```bash
   git clone https://github.com/yourusername/na_ponimanii.git
   cd na_ponimanii
   ```

2. Make sure you have a valid `.env` file with all required environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   nano .env
   ```

3. Make all scripts executable:
   ```bash
   chmod +x deploy.sh uninstall.sh status.sh restart.sh update.sh setup_cron_update.sh
   ```

4. Run the deployment script:
   ```bash
   sudo ./deploy.sh
   ```

   This script will:
   - Copy all project files to `/opt/na_ponimanii/`
   - Install required Python dependencies
   - Set up systemd services
   - Start the bot and server

5. Verify that the services are running:
   ```bash
   systemctl status na_ponimanii_bot
   systemctl status na_ponimanii_server
   ```

## Managing the Services

### Checking Status

You can use the provided status script to check the status of both services:

```bash
./status.sh
```

This script will show:
- Whether the services are running
- Detailed status information
- Instructions for viewing logs

### Checking Logs

You can view the logs using journalctl:

```bash
# View bot logs
journalctl -u na_ponimanii_bot -f

# View server logs
journalctl -u na_ponimanii_server -f
```

### Restarting Services

You can use the provided restart script to restart both services:

```bash
sudo ./restart.sh
```

Or restart them manually:

```bash
sudo systemctl restart na_ponimanii_bot
sudo systemctl restart na_ponimanii_server
```

### Stopping Services

To stop the services:

```bash
sudo systemctl stop na_ponimanii_bot
sudo systemctl stop na_ponimanii_server
```

### Disabling Services

To disable the services from starting at boot:

```bash
sudo systemctl disable na_ponimanii_bot
sudo systemctl disable na_ponimanii_server
```

## Updating the Application

To update the application with the latest code from GitHub:

```bash
sudo ./update.sh
```

This script will:
1. Clone the latest version from GitHub
2. Preserve your existing `.env` file
3. Create a backup of the current installation
4. Update the files in the installation directory
5. Update dependencies
6. Restart the services

If there are any issues after updating, you can find a backup of the previous version in `/opt/na_ponimanii.backup.[timestamp]`.

### Customizing the Update Script

Before using the update script, make sure to edit it and set the correct GitHub repository URL and branch:

```bash
# Open the script in an editor
nano update.sh

# Update these lines with your repository information
GITHUB_REPO="https://github.com/yourusername/na_ponimanii.git"
BRANCH="main"
```

## Setting Up Automatic Updates

You can set up automatic updates using the provided script:

```bash
sudo ./setup_cron_update.sh
```

This script will:
1. Ask you to choose an update schedule (daily, weekly, monthly, or custom)
2. Create a cron job to run the update script on the selected schedule
3. Set up logging for the automatic updates

The update logs will be written to `/opt/na_ponimanii/logs/update_cron.log`.

### Removing Automatic Updates

To remove the automatic update cron job:

```bash
sudo rm /etc/cron.d/na_ponimanii_update
```

## Uninstallation

If you need to remove the services:

```bash
sudo ./uninstall.sh
```

This script will:
- Stop and disable the systemd services
- Remove the service files
- Optionally remove the installation directory

## Troubleshooting

If you encounter issues:

1. Check the service status:
   ```bash
   systemctl status na_ponimanii_bot
   systemctl status na_ponimanii_server
   ```

2. Check the logs:
   ```bash
   journalctl -u na_ponimanii_bot -e
   journalctl -u na_ponimanii_server -e
   ```

3. Verify that the `.env` file contains the correct configuration.

4. Ensure that the Python dependencies are installed correctly:
   ```bash
   pip3 install -r /opt/na_ponimanii/requirements.txt
   ```

5. Check file permissions:
   ```bash
   ls -la /opt/na_ponimanii/