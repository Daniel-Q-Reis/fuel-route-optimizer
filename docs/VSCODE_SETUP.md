# VS Code & Dev Container Setup

This project is fully configured to be used with the [VS Code Dev Containers](https://code.visualstudio.com/docs/devcontainers/containers) extension. This is the **highly recommended** workflow for a seamless, integrated development experience.

## 🚀 First-Time Setup

1.  **Generate Project & Initialize Git:** Follow the instructions in the main `README.md` to generate your project folder and run `git init` and create your first commit.

2.  **Reopen in Container:** Open the generated project folder in VS Code. A notification will appear in the bottom-right corner suggesting you "Reopen in Container". Click it. VS Code will build the container and connect to it.

3.  **Configure Git Identity (One-Time Step):** The container is a new, clean machine and doesn't know your Git identity. You must configure it once to be able to create commits. Open a terminal inside VS Code (`Ctrl+`` `) and run these commands with your details:

    ```bash
    git config --global user.name "Your Name"
    git config --global user.email "you@example.com"
    ```

    Now you can create commits from within the Dev Container.

---

## Alternative: Manual Docker Integration

If you prefer not to use the Dev Container feature, you can connect VS Code to the Docker environment manually as described below.

## 🚀 Quick Setup

### 1. Install Recommended Extensions

VS Code will automatically suggest the recommended extensions when you open the project:

```bash
# Open the project in VS Code
code .
```

Click **"Install All"** or manually install the essential ones:
- **Python** (ms-python.python)
- **Django** (batisteo.vscode-django)
- **Docker** (ms-azuretools.vscode-docker)
- **Black Formatter** (ms-python.black-formatter)
- **Ruff** (charliermarsh.ruff)

### 2. Start the Docker Environment

**Option A: Via Shortcut (Recommended)**
```
Ctrl+Shift+U (starts containers)
```

**Option B: Via Task**
```
Ctrl+Shift+P → Tasks: Run Task → App: Up
```

**Option C: Via Terminal**
```bash
docker-compose up -d --build
```

### 3. Integrated Terminal (Automatic)

The VS Code terminal is already configured to open **directly in the container**:
- Press `Ctrl+`` `
- The terminal automatically opens in the web container
- All Django commands work directly:

```bash
# Already inside the container:
python manage.py shell
python manage.py migrate
pytest
```

## ⚡ Productivity Shortcuts

### Custom Shortcuts

| Action | Shortcut | Description |
|---|---|---|
| **Start App** | `Ctrl+Shift+U` | Starts containers |
| **Stop App** | `Ctrl+Shift+D` | Stops containers |
| **Run Tests** | `Ctrl+Shift+T` | Runs pytest |
| **Django Shell** | `Ctrl+Shift+S` | Opens Django shell |
| **Migrations** | `Ctrl+Shift+M` | Runs migrate |
| **View Logs** | `Ctrl+Shift+L` | Shows real-time logs |
| **Container Bash** | `Ctrl+Shift+B` | Enters the container |

### Useful Default Shortcuts

| Action | Shortcut | Description |
|---|---|---|
| **Command Palette** | `Ctrl+Shift+P` | Command menu |
| **Quick Open** | `Ctrl+P` | Open files |
| **Terminal** | `Ctrl+`` ` | Integrated terminal |
| **Debug** | `F5` | Start debugging |
| **Format Document** | `Shift+Alt+F` | Format code |

## 🐛 Advanced Debugging

### Debugpy Setup

Debugpy is already configured and working:

1.  **Set breakpoints** in your code
2.  **Press F5** → choose `Django: Attach to debugpy (Docker)`
3.  **The debugger automatically connects** to the container

### Debugging Tests

```bash
# Set a breakpoint in a test
# Press F5 → Django: Debug Tests
```

### Manual Debugging

If you need to start it manually:
```bash
# Via task
Ctrl+Shift+P → Tasks: Run Task → Debug: Start with debugpy

# Waits for VS Code to connect
# Then F5 → Django: Attach to debugpy (Docker)
```

## 🧪 Integrated Testing

### Running Tests

**Via Shortcut:**
```
Ctrl+Shift+T (runs all tests)
```

**Via Command Palette:**
```
Ctrl+Shift+P → Python: Run All Tests
```

**Via Tasks:**
```
Ctrl+Shift+P → Tasks: Run Task → Test: Run All Tests
Ctrl+Shift+P → Tasks: Run Task → Test: Run Tests with Coverage
```

### Test Explorer

VS Code will automatically discover your tests:
- **Testing Panel** (beaker icon in the sidebar)
- **Run/Debug individual tests**
- **Integrated coverage**

## 🔧 Available Tasks

Access via `Ctrl+Shift+P` → `Tasks: Run Task`:

### Docker Management
- **App: Up** - Starts containers
- **App: Down (keep volumes)** - Stops containers
- **DB: Reset (danger)** - Full database reset
- **Docker: View Logs** - Real-time logs
- **Docker: Container Status** - Status of containers
- **Docker: Enter Web Container** - Bash in the container

### Django Operations
- **Django: Migrate** - Run migrations
- **Django: Make Migrations** - Create migrations
- **Django: Shell** - Interactive shell
- **Django: Create Superuser** - Create a superuser
- **Django: Collect Static Files** - Collect static files

### Testing & Quality
- **Test: Run All Tests** - Run all tests
- **Test: Run Tests with Coverage** - Tests with coverage
- **Code: Run Black Formatter** - Code formatting
- **Code: Run Ruff Linter** - Code linting

### Debugging
- **Debug: Start with debugpy** - Start with debug

## 📁 VS Code File Structure

```
.vscode/
├── settings.json      # Workspace settings
├── tasks.json         # Custom tasks
├── launch.json        # Debug configurations
├── extensions.json    # Recommended extensions
└── keybindings.json   # Custom shortcuts
```

## 🔍 Database Integration

### PostgreSQL Client

Configure the PostgreSQL extension:
- **Host:** `localhost`
- **Port:** `5432`
- **Database:** `master_template_db`
- **User:** `postgres`
- **Password:** `postgres`

### Quick Access

```bash
# Via integrated terminal (already in the container):
psql -h db -U postgres -d master_template_db
```

## 🛠️ Troubleshooting

### Problem: "Terminal doesn't open in the container"

**Solutions:**
1.  Make sure the containers are running: `docker-compose ps`
2.  Restart VS Code
3.  Use `Ctrl+Shift+B` to manually enter the container

### Problem: "Tests are not discovered"

**Solutions:**
1.  Check if the containers are running
2.  Reload window: `Ctrl+Shift+P` → `Developer: Reload Window`
3.  Run manually: `Ctrl+Shift+T`

### Problem: "Debugger doesn't connect"

**Solutions:**
1.  Check if the web container is healthy: `docker-compose ps`
2.  Restart containers: `Ctrl+Shift+D` → `Ctrl+Shift+U`
3.  Check port 5678: `netstat -an | findstr 5678`

### Problem: "Import errors in VS Code"

**Solutions:**
1.  Containers must be running for code analysis
2.  Reload window: `Ctrl+Shift+P` → `Developer: Reload Window`
3.  Check if services are healthy

### Problem: "Task fails on Windows"

**Solutions:**
1.  Make sure Docker Desktop is running
2.  Use PowerShell as an administrator if necessary
3.  Check if `docker-compose` is in the PATH

## 💡 Productivity Tips

### Senior Workflow

1.  **Start of the day:**
    ```
    Ctrl+Shift+U (starts the environment)
    Ctrl+` (opens the terminal in the container)
    ```

2.  **During development:**
    ```
    Ctrl+Shift+T (runs tests)
    F5 (debug when necessary)
    Ctrl+Shift+M (migrations)
    ```

3.  **End of the day:**
    ```
    Ctrl+Shift+D (stops containers)
    ```

### Multi-cursor and Editing

- **Alt+Click** - Multi-cursor
- **Ctrl+D** - Select next occurrence
- **Alt+Up/Down** - Move line
- **Shift+Alt+Up/Down** - Duplicate line

### Quick Actions

- **Ctrl+P** - Quick Open (files)
- **Ctrl+Shift+P** - Command Palette
- **Ctrl+T** - Go to symbol
- **F12** - Go to definition
- **Shift+F12** - Find references

## 🎨 Customization

### Recommended Themes

- **Material Theme Darker High Contrast**
- **One Dark Pro**
- **Dracula Official**

### Extra Settings

Edit `.vscode/settings.json` to customize:

```json
{
  "workbench.colorTheme": "Material Theme Darker High Contrast",
  "workbench.iconTheme": "material-icon-theme",
  "editor.fontSize": 14,
  "editor.lineHeight": 1.5,
  "terminal.integrated.fontSize": 13
}
```

## 📚 Advanced Resources

### REST Client

Create `.http` files to test APIs:

```http
### Get API Root
GET http://localhost:8000/api/

### Login
POST http://localhost:8000/api/auth/login/
Content-Type: application/json

{
  "username": "admin",
  "password": "admin123"
}
```

### Git Integration

- **GitLens** is already installed
- **Source Control:** `Ctrl+Shift+G`
- **Git Graph** for visualization

### Database Queries

Use the PostgreSQL extension to run queries directly in VS Code.

## 🎆 Configuration Summary

✅ **Integrated terminal** opens directly in the container
✅ **Custom shortcuts** for all operations
✅ **Remote debugging** with debugpy configured
✅ **Integrated testing** with automatic discovery
✅ **Complete tasks** for Django and Docker
✅ **Automatic formatting** with Black and Ruff
✅ **Optimized extensions** for Django/Docker

**Result: Senior-level development environment!** 🚀

## 🔗 Useful Links

- [Django Master Template Repository](https://github.com/Daniel-Q-Reis/master-tamplate)
- [VS Code Python Documentation](https://code.visualstudio.com/docs/python/python-tutorial)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Django Documentation](https://docs.djangoproject.com/)
