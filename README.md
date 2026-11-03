# product-management-team-8

AI-powered real-time usage tracking proof of concept for public gyms.

## Setup

You need Python 3 installed.

### 1. Clone the repo

```bash
git clone https://github.com/jack-emo/product-management-team-8.git
cd product-management-team-8
```

### 2. Create a virtual environment

**macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (Command Prompt)**

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**Windows (PowerShell)**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell blocks the activate script, run this once, then activate again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### 3. Create your env file and add the API key

Copy the example file, then open `.env` and replace `Your_Google_API_Key_Here` with a [Google AI Studio API key](https://aistudio.google.com/apikey).

**macOS**

```bash
cp .env.example .env
```

**Windows (Command Prompt)**

```cmd
copy .env.example .env
```

**Windows (PowerShell or Git Bash)**

```powershell
cp .env.example .env
```

`.env` should look like this:

```
GOOGLE_API_KEY="your-key-here"
```

`.env` is listed in `.gitignore`, so the key stays on your machine.

The app reads `GOOGLE_API_KEY` from the environment. Load `.env` in the same terminal session before you run it.

**macOS**

```bash
set -a
source .env
set +a
python main.py
```

**Windows (PowerShell)**

```powershell
Get-Content .env | ForEach-Object {
  if ($_ -match '^\s*([^#=]+)=(.*)$') {
    Set-Item -Path "Env:$($matches[1].Trim())" -Value $matches[2].Trim().Trim('"')
  }
}
python main.py
```

**Windows (Command Prompt)**

```cmd
set GOOGLE_API_KEY=your-key-here
python main.py
```
