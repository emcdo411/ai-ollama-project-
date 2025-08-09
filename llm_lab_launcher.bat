@echo off
setlocal EnableDelayedExpansion

rem === CONFIG (edit if needed) ===============================================
set "OLLAMA_DIR=C:\Users\Veteran\AppData\Local\Programs\Ollama"
set "MODEL=mistral:7b"
set "LAB_DIR=%~dp0"
set "VENV_DIR=%LAB_DIR%.venv"
rem ===========================================================================

rem Helper: add Ollama to PATH for this session
set "PATH=%PATH%;%OLLAMA_DIR%"

:main_menu
cls
echo.
echo ================== Local LLM Lab Launcher ==================
echo  Lab Dir : %LAB_DIR%
echo  Venv    : %VENV_DIR%
echo  Ollama  : %OLLAMA_DIR%
echo  Model   : %MODEL%
echo ============================================================
echo  1) Check Ollama and PATH
echo  2) Start Ollama server
echo  3) Stop Ollama server (best-effort)
echo  4) Pull model (%MODEL%)
echo  5) Create venv + install requirements
echo  6) Activate venv (this window)
echo  7) Run chain test (Analyze -> Plan -> Generate)
echo  8) Build RAG index (data/sample_docs)
echo  9) Ask RAG question (prompt)
echo 10) Run evals
echo 11) Change model (e.g., mistral:7b-instruct) [session]
echo 12) Exit
echo ============================================================
set /p CHOICE=Select an option (1-12): 

if "%CHOICE%"=="1" goto check_ollama
if "%CHOICE%"=="2" goto start_server
if "%CHOICE%"=="3" goto stop_server
if "%CHOICE%"=="4" goto pull_model
if "%CHOICE%"=="5" goto make_venv
if "%CHOICE%"=="6" goto activate_venv
if "%CHOICE%"=="7" goto run_chain
if "%CHOICE%"=="8" goto build_rag
if "%CHOICE%"=="9" goto ask_rag
if "%CHOICE%"=="10" goto run_evals
if "%CHOICE%"=="11" goto change_model
if "%CHOICE%"=="12" goto end
echo Invalid choice.
pause
goto main_menu

:check_ollama
echo.
echo Checking Ollama...
where ollama
if errorlevel 1 (
  echo.
  echo [X] 'ollama' not found in PATH for this session.
  echo Trying direct path: "%OLLAMA_DIR%\ollama.exe"
  if exist "%OLLAMA_DIR%\ollama.exe" (
    "%OLLAMA_DIR%\ollama.exe" --version
  ) else (
    echo [X] Could not find ollama.exe in %OLLAMA_DIR%
    echo     Update OLLAMA_DIR at top of this file, or reinstall Ollama.
  )
) else (
  ollama --version
)
pause
goto main_menu

:start_server
echo.
echo Starting Ollama server (minimized)...
if exist "%OLLAMA_DIR%\ollama.exe" (
  start /min "" "%OLLAMA_DIR%\ollama.exe" serve
) else (
  start /min "" ollama serve
)
echo Waiting 3s...
timeout /t 3 >nul
echo Done.
pause
goto main_menu

:stop_server
echo.
echo Attempting to stop Ollama server...
rem Graceful stop is not exposed in CLI; best-effort kill by image name:
taskkill /IM ollama.exe /F >nul 2>&1
echo If the server was running, it should be terminated now.
pause
goto main_menu

:pull_model
echo.
echo Pulling model: %MODEL%
if exist "%OLLAMA_DIR%\ollama.exe" (
  "%OLLAMA_DIR%\ollama.exe" pull %MODEL%
) else (
  ollama pull %MODEL%
)
pause
goto main_menu

:make_venv
echo.
echo Creating venv (if missing) and installing requirements...
if not exist "%VENV_DIR%\Scripts\python.exe" (
  python -m venv "%VENV_DIR%"
)
call "%VENV_DIR%\Scripts\activate"
pip install --upgrade pip
pip install -r "%LAB_DIR%requirements.txt"
echo Done.
pause
goto main_menu

:activate_venv
echo.
if exist "%VENV_DIR%\Scripts\activate.bat" (
  call "%VENV_DIR%\Scripts\activate"
  where python
  python --version
) else (
  echo [X] No venv found at %VENV_DIR%
  echo Create it via menu option 5 first.
)
pause
goto main_menu

:run_chain
echo.
call "%VENV_DIR%\Scripts\activate"
echo Running chain test...
python "%LAB_DIR%scripts\run_chain.py" --task "Summarize this paragraph in 3 bullets" --input "Mistral is a capable small model for local use."
echo.
pause
goto main_menu

:build_rag
echo.
call "%VENV_DIR%\Scripts\activate"
echo Building FAISS index from data\sample_docs...
python "%LAB_DIR%scripts\build_index.py" --docs "%LAB_DIR%data\sample_docs"
echo.
pause
goto main_menu

:ask_rag
echo.
call "%VENV_DIR%\Scripts\activate"
set /p Q=Enter your question: 
if "%Q%"=="" (
  echo No question entered.
  pause
  goto main_menu
)
python "%LAB_DIR%scripts\ask_rag.py" --question "%Q%"
echo.
pause
goto main_menu

:run_evals
echo.
call "%VENV_DIR%\Scripts\activate"
python "%LAB_DIR%scripts\run_evals.py"
echo.
pause
goto main_menu

:change_model
echo.
set /p NEWMODEL=Enter new model tag (e.g., mistral:7b-instruct): 
if "%NEWMODEL%"=="" (
  echo No change made.
) else (
  set "MODEL=%NEWMODEL%"
  echo Model set to: %MODEL%
)
pause
goto main_menu

:end
echo Bye!
endlocal
exit /b 0
