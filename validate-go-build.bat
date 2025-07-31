@echo off
echo === Chorus Go Services Build Validation ===
echo.

echo [1/4] Testing workflow-engine...
cd services\workflow-engine
go mod tidy
go build -o main.exe .
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: workflow-engine build failed!
    pause
    exit /b 1
)
echo SUCCESS: workflow-engine builds correctly
del main.exe 2>nul
cd ..\..
echo.

echo [2/4] Testing websocket-gateway...
cd services\websocket-gateway
go mod tidy
go build -o main.exe .
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: websocket-gateway build failed!
    pause
    exit /b 1
)
echo SUCCESS: websocket-gateway builds correctly
del main.exe 2>nul
cd ..\..
echo.

echo [3/4] Testing presence-service...
cd services\presence-service
go mod tidy
go build -o main.exe .
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: presence-service build failed!
    pause
    exit /b 1
)
echo SUCCESS: presence-service builds correctly
del main.exe 2>nul
cd ..\..
echo.

echo [4/4] All Go services validated successfully!
echo.
echo === Ready for Docker build ===
echo You can now run: docker-compose -f infrastructure/docker-compose.yml up --build
pause