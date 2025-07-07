#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Install Python packages
echo "--- Installing Python packages from requirements.txt ---"
pip install --user -r requirements.txt

# Now that playwright is installed, add its location to the PATH
# So the 'sudo' command can find it.
export PATH="$HOME/.local/bin:$PATH"

# Install system dependencies using the newly installed playwright
echo "--- Installing system dependencies for Playwright ---"
sudo playwright install-deps

# Install the Chromium browser
echo "--- Installing Chromium browser ---"
playwright install chromium

echo "--- Environment setup complete! ---"
