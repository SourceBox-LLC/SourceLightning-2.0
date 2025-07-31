<div align="center">
  <img src="lightning MD logo.png" alt="LightningMD Logo" width="200" height="200">
  
  # ⚡ LightningMD
  
  **AI-Powered Documentation Generator**
  
  <p>LightningMD is a powerful, modern documentation generator that leverages local AI models to create comprehensive, professional documentation for your software projects. Built with a beautiful Flet UI and powered by Ollama, it transforms your GitHub repositories and local projects into well-structured, detailed documentation.</p>
</div>

![LightningMD Interface](https://img.shields.io/badge/UI-Flet-purple?style=for-the-badge) ![AI Model](https://img.shields.io/badge/AI-Ollama-blue?style=for-the-badge) ![Python](https://img.shields.io/badge/Python-3.8+-green?style=for-the-badge)

## 🌟 Features

### 🎯 **Core Functionality**
- **Dual Source Support**: Process both GitHub repositories and local project folders
- **AI-Powered Analysis**: Uses local Ollama models for intelligent code analysis
- **Vector Database**: ChromaDB integration for efficient project indexing
- **Real-time Processing**: Live progress tracking with detailed status updates
- **Professional Output**: Generates comprehensive, structured documentation

### 🎨 **Modern User Interface**
- **Beautiful Purple Theme**: Professional, dark-themed interface
- **Responsive Design**: Clean, centered layout with intuitive navigation
- **Live Progress Tracking**: Visual progress indicators and status updates
- **Markdown Rendering**: Beautiful documentation display with syntax highlighting
- **Copy & Download**: Easy documentation export and sharing

### ⚙️ **Advanced Settings**
- **Dynamic Model Detection**: Automatically detects installed Ollama models
- **Model Compatibility Testing**: Tests agent/function-calling support
- **Connection Testing**: Verifies Ollama server connectivity
- **Settings Management**: Save/cancel changes with confirmation dialogs
- **Current Model Display**: Always shows which model is generating docs

### 🔧 **Technical Features**
- **Persistent Vector Storage**: Efficient project caching and reuse
- **Agent-Based Processing**: Intelligent tool usage for comprehensive analysis
- **Error Handling**: Robust error management and user feedback
- **Progress Visualization**: Step-by-step processing with visual indicators
- **Clean Architecture**: Modular design with separated concerns

## 📋 Prerequisites

### Required Software
1. **Python 3.8+** - Programming language runtime
2. **Ollama** - Local AI model server
3. **Git** - Version control system (for GitHub repositories)

### Ollama Setup
1. Install Ollama from [ollama.ai](https://ollama.ai)
2. Install a compatible model (recommended: `qwen3`):
   ```bash
   ollama pull qwen3
   ```
3. Ensure Ollama is running:
   ```bash
   ollama serve
   ```

## 🚀 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/SourceBox-LLC/SourceLightning-2.0.git
cd SourceLightning-2.0
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Launch Application
```bash
python main.py
```

## 🎯 Quick Start Guide

### 1. **Launch LightningMD**
   - Run `python main.py`
   - The application opens with a beautiful purple-themed interface
   - Current model is displayed in the header

### 2. **Choose Your Source**
   - **GitHub Repository**: Select "GitHub Repository" and enter the URL
   - **Local Folder**: Select "Local Folder" and browse to your project

### 3. **Customize Documentation** (Optional)
   - Enter a custom prompt in the "Documentation Prompt" field
   - Default: "Generate a comprehensive README with installation instructions and examples"

### 4. **Generate Documentation**
   - Click "Generate Documentation"
   - Watch live progress updates as your project is processed
   - Documentation automatically opens when complete

### 5. **Review and Export**
   - View beautifully rendered markdown documentation
   - Copy to clipboard or download as README.md
   - Use the back button to generate more documentation

## ⚙️ Configuration

### Settings Page
Access via the settings icon (⚙️) in the top-right corner:

#### **Ollama Configuration**
- **Server URL**: Default `http://localhost:11434`
- **Model Selection**: Choose from installed Ollama models
- **Connection Test**: Verify server connectivity
- **Compatibility Test**: Check model agent support

#### **Settings Management**
- **Change Detection**: Save button activates when changes are made
- **Confirmation Dialog**: Confirm or cancel changes before applying
- **Real-time Updates**: Main page model display updates automatically

### Environment Variables
Optional configuration via environment variables:
```bash
OLLAMA_URL=http://localhost:11434  # Ollama server URL
DEFAULT_MODEL=qwen3               # Default model name
```

## 📖 Usage Examples

### Example 1: GitHub Repository
```
1. Select "GitHub Repository"
2. Enter: https://github.com/username/project
3. Custom prompt: "Create API documentation with code examples"
4. Click "Generate Documentation"
```

### Example 2: Local Project
```
1. Select "Local Folder"
2. Browse to your project directory
3. Use default prompt or customize
4. Click "Generate Documentation"
```

### Example 3: Custom Documentation
```
Prompt: "Generate technical documentation focusing on:
- Architecture overview
- API endpoints with examples
- Deployment instructions
- Troubleshooting guide"
```

## 🏗️ Architecture

### Core Components
- **`main.py`**: Flet UI application and main orchestration
- **`agent.py`**: AI agent with tool-based project analysis
- **`project_setup.py`**: Project processing and vector database management
- **`requirements.txt`**: Python dependencies

### Data Flow
1. **Input Processing**: GitHub clone or local folder selection
2. **Vectorization**: ChromaDB indexing of project files
3. **AI Analysis**: Ollama agent processes project structure
4. **Documentation Generation**: Structured markdown output
5. **UI Presentation**: Beautiful rendering with export options

### Vector Database
- **Storage**: `./chroma_db/` directory
- **Collections**: Named by project (e.g., `repo_project-name`)
- **Persistence**: Automatic cleanup and reuse
- **CLI Management**: Built-in collection management

## 🛠️ Troubleshooting

### Common Issues

#### **"Connection failed" Error**
- Ensure Ollama is running: `ollama serve`
- Check server URL in settings (default: `http://localhost:11434`)
- Test connection using the "Test Connection" button

#### **"Model not found" Error**
- Install the model: `ollama pull qwen3`
- Refresh models in settings
- Select an available model from the dropdown

#### **"Agent compatibility" Issues**
- Use the "Test Agent Compatibility" button
- Try a different model (some models don't support function calling)
- Check Ollama version compatibility

#### **GitHub Clone Failures**
- Ensure Git is installed and accessible
- Check repository URL format
- Verify internet connection for public repos
- For private repos, ensure proper authentication

#### **Local Folder Issues**
- Ensure folder contains readable files
- Check folder permissions
- Verify the folder contains a software project

### Performance Tips
- **Model Selection**: Larger models provide better documentation but are slower
- **Project Size**: Very large projects may take longer to process
- **Vector Reuse**: Previously processed projects load faster
- **Hardware**: More RAM and CPU cores improve performance

## 🔧 Advanced Usage

### Custom Prompts
Tailor documentation generation with specific prompts:

```
# API-focused documentation
"Generate comprehensive API documentation with:
- Endpoint descriptions and parameters
- Request/response examples
- Authentication methods
- Rate limiting information"

# User guide focused
"Create user-friendly documentation with:
- Step-by-step tutorials
- Screenshots and examples
- FAQ section
- Troubleshooting guide"

# Developer documentation
"Generate technical documentation including:
- Architecture diagrams
- Code structure analysis
- Development setup
- Contributing guidelines"
```

### Vector Database Management
The application automatically manages ChromaDB collections:

- **Automatic Naming**: Collections named by project
- **Persistence**: Data survives application restarts
- **Cleanup**: Temporary files automatically removed
- **Reuse**: Previously processed projects load instantly

## 🤝 Contributing

We welcome contributions to LightningMD! Here's how to get started:

### Development Setup
1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Install development dependencies
4. Make your changes
5. Test thoroughly
6. Submit a pull request

### Code Style
- Follow PEP 8 Python style guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Include type hints where appropriate

### Testing
- Test with multiple Ollama models
- Verify both GitHub and local folder processing
- Check UI responsiveness and error handling
- Validate documentation output quality

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **Flet Team**: For the amazing Python UI framework
- **Ollama**: For making local AI models accessible
- **ChromaDB**: For efficient vector storage
- **Open Source Community**: For inspiration and support

## 📞 Support

Need help? Here are your options:

- **Issues**: Report bugs on [GitHub Issues](https://github.com/SourceBox-LLC/SourceLightning-2.0/issues)
- **Discussions**: Join conversations on [GitHub Discussions](https://github.com/SourceBox-LLC/SourceLightning-2.0/discussions)
- **Documentation**: Check this README for detailed information

---

**⚡ LightningMD - Transform your code into beautiful documentation with the power of AI!**

*Built with ❤️ using Flet, Ollama, and ChromaDB*
