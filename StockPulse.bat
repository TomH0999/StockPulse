@echo off
REM Lancement local en un clic (Windows) : installe les dependances au premier lancement, puis ouvre StockPulse dans le navigateur.
cd /d "%~dp0"
if not exist "frontend\dist\index.html" (
  echo Premiere installation...
  python -m pip install -r backend\requirements.txt || goto :error
  pushd frontend
  call npm install || goto :error
  call npx vite build || goto :error
  popd
)
start "" http://127.0.0.1:8000
cd backend
python main.py
goto :eof
:error
echo Echec de l'installation. Verifiez que Python 3.11+ et Node.js sont installes.
pause
