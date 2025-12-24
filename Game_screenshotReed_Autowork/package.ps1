$ErrorActionPreference = "Stop"

Write-Host "Installing dependencies..."
..\.venv\Scripts\pip install pyinstaller scrcpy-client av flask opencv-python numpy ddddocr adbutils

Write-Host "Building with PyInstaller..."
..\.venv\Scripts\python -m PyInstaller --clean --noconfirm --distpath dist StellasoraMaster.spec

Write-Host "Copying resources..."
$dest = "dist\StellasoraMaster"

# Function to copy with overwrite
function Copy-ToDist ($path) {
    if (Test-Path $path) {
        Write-Host "Copying $path..."
        Copy-Item -Path $path -Destination $dest -Recurse -Force
    } else {
        Write-Warning "$path not found!"
    }
}

Copy-ToDist "core"
Copy-ToDist "webapp"
Copy-ToDist "run_app.py"
Copy-ToDist "templates_zh-CN"
Copy-ToDist "templates_zh-Hant"
Copy-ToDist "config.json"

# Handle version.txt
if (-not (Test-Path "version.txt")) {
    Write-Host "Creating version.txt..."
    "1.0.0" | Out-File "version.txt" -Encoding utf8
}
Copy-ToDist "version.txt"

Write-Host "Packaging complete! Output in $dest"
