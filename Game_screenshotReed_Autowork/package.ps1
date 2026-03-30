$ErrorActionPreference = "Stop"

function Invoke-Step ($message, [scriptblock]$action) {
    Write-Host $message
    & $action
}

function Reset-Dir ($path) {
    if (Test-Path $path) {
        Remove-Item -Path $path -Recurse -Force
    }
    New-Item -ItemType Directory -Path $path | Out-Null
}

function Copy-ToDist ($path) {
    if (Test-Path $path) {
        Write-Host "Copying $path..."
        Copy-Item -Path $path -Destination $dest -Recurse -Force
    } else {
        Write-Warning "$path not found!"
    }
}

Invoke-Step "Installing Python packaging dependencies..." {
    ..\.venv\Scripts\pip install pyinstaller scrcpy-client av flask opencv-python numpy ddddocr adbutils
}

Invoke-Step "Building frontend assets..." {
    Push-Location "webapp\frontend"
    try {
        if (-not (Test-Path "node_modules")) {
            npm ci
        }
        npm run build
    }
    finally {
        Pop-Location
    }
}

Invoke-Step "Building with PyInstaller..." {
    ..\.venv\Scripts\python -m PyInstaller --clean --noconfirm --distpath dist StellasoraMaster.spec
}

Write-Host "Copying runtime resources..."
$dest = "dist\StellasoraMaster"
$destWebApp = Join-Path $dest "webapp"

Copy-ToDist "core"
Copy-ToDist "run_app.py"
Copy-ToDist "templates_zh-CN"
Copy-ToDist "templates_zh-Hant"
Copy-ToDist "config.json"

Reset-Dir $destWebApp
Copy-Item -Path "webapp\app.py" -Destination $destWebApp -Force
Copy-Item -Path "webapp\__init__.py" -Destination $destWebApp -Force
Copy-Item -Path "webapp\static" -Destination $destWebApp -Recurse -Force

if (-not (Test-Path "version.txt")) {
    Write-Host "Creating version.txt..."
    "1.0.0" | Out-File "version.txt" -Encoding utf8
}
Copy-ToDist "version.txt"

Write-Host "Packaging complete! Output in $dest"
