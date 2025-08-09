@echo off
setlocal

REM === 1. Ensure Ollama is in PATH ===
set OLLAMA_DIR=C:\Users\Veteran\AppData\Local\Programs\Ollama
echo Adding Ollama to PATH (for this session)...
set PATH=%PATH%;%OLLAMA_DIR%

REM === 2. Check Ollama version ===
echo Checking Ollama...
ollama --version
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Ollama not found! Make sure it's installed.
    pause
    exit /b
)

REM === 3. Start Ollama server in the background ===
echo Starting Ollama server...
start /min "" "%OLLAMA_DIR%\ollama.exe" serve
timeout /t 3 > nul

REM === 4. Pull Mistral 7B if not already present ===
echo Checking for Mistral 7B model...
ollama list | findstr /i "mistral:7b" > nul
if %ERRORLEVEL% NEQ 0 (
    echo Pulling Mistral 7B model (first time only)...
    ollama pull mistral:7b
) else (
    echo Mistral 7B already installed.
)

REM === 5. Activate Python venv ===
echo Activating Python virtual environment...
call .venv\Scripts\activate

REM === 6. Run a quick pipeline test ===
echo Running Local LLM Lab test...
python scripts\run_chain.py --task "Summarize this paragraph in 3 bullets" --input "Mistral is a capable small model for local use."

echo Done!
pause
