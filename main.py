import flet as ft
import threading
import time
from project_setup import process_project, vectorize_repository
from agent import search_repository, list_repository_collections, analyze_repository_structure, get_file_content
from ollama import chat

def main(page: ft.Page):
    # Set page properties
    page.title = "LightningMD - Documentation Generator"
    page.bgcolor = ft.Colors.BLACK
    page.window_width = 1000
    page.window_height = 700
    page.window_resizable = True
    page.scroll = ft.ScrollMode.AUTO
    page.theme_mode = ft.ThemeMode.DARK
    
    # Page state management to prevent duplication
    current_page_state = {"current": "main"}  # Track current page state
    current_view = "main"  # "main" or "documentation"
    generated_documentation = ""
    project_info = {}
    
    def clean_documentation(text):
        """Remove <think></think> tags and other internal model thoughts from documentation"""
        import re
        if not text:
            return text
        
        # Remove <think>...</think> blocks (including multiline)
        cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove any remaining think tags that might be malformed
        cleaned = re.sub(r'</?think[^>]*>', '', cleaned, flags=re.IGNORECASE)
        
        # Clean up extra whitespace that might be left behind
        cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned)  # Replace multiple newlines with double newlines
        cleaned = cleaned.strip()  # Remove leading/trailing whitespace
        
        return cleaned
    
    def show_main_page():
        """Switch to the main page view"""
        nonlocal current_view
        current_view = "main"
        build_main_page()
        page.update()
    
    def show_settings_page():
        """Switch to the settings page view"""
        nonlocal current_view
        current_view = "settings"
        build_settings_page()
        page.update()
    
    # Placeholder for navigation functions - will be defined after main_page_content
    
    def build_settings_page():
        """Build and display the settings page"""
        if current_page_state["current"] == "settings":
            return  # Already on settings page, prevent duplication
        
        current_page_state["current"] = "settings"
        page.controls.clear()
        
        # Settings state variables
        ollama_url = ft.Ref[ft.TextField]()
        model_dropdown = ft.Ref[ft.Dropdown]()
        test_button = ft.Ref[ft.ElevatedButton]()
        compatibility_button = ft.Ref[ft.ElevatedButton]()
        status_icon = ft.Ref[ft.Icon]()
        status_text = ft.Ref[ft.Text]()
        compatibility_icon = ft.Ref[ft.Icon]()
        compatibility_text = ft.Ref[ft.Text]()
        refresh_models_button = ft.Ref[ft.IconButton]()
        save_button = ft.Ref[ft.ElevatedButton]()
        
        def get_available_models(url="http://localhost:11434"):
            """Get list of available models from Ollama server"""
            try:
                import requests
                response = requests.get(f"{url}/api/tags", timeout=5)
                if response.status_code == 200:
                    models = response.json().get('models', [])
                    # Extract model names and clean them
                    model_names = []
                    for model in models:
                        name = model.get('name', '')
                        # Remove version tags (e.g., 'qwen3:latest' -> 'qwen3')
                        clean_name = name.split(':')[0] if ':' in name else name
                        if clean_name and clean_name not in model_names:
                            model_names.append(clean_name)
                    return sorted(model_names)
                else:
                    return ["qwen3"]  # Fallback
            except Exception:
                return ["qwen3"]  # Fallback
        
        # Get initial list of available models first
        initial_models = get_available_models()
        
        # Track original settings for change detection
        original_settings = {
            "url": "http://localhost:11434",
            "model": initial_models[0] if initial_models else "qwen3"
        }
        
        def check_for_changes():
            """Check if settings have changed from original values"""
            current_url = ollama_url.current.value or "http://localhost:11434"
            current_model = model_dropdown.current.value or original_settings["model"]
            
            has_changes = (
                current_url != original_settings["url"] or
                current_model != original_settings["model"]
            )
            
            # Update save button state
            if save_button.current:
                save_button.current.disabled = not has_changes
                if has_changes:
                    save_button.current.style.bgcolor = ft.Colors.GREEN_600
                    save_button.current.text = "Save Changes"
                else:
                    save_button.current.style.bgcolor = ft.Colors.GREY_600
                    save_button.current.text = "No Changes"
                page.update()
        
        def on_settings_change(e):
            """Called when any setting is changed"""
            check_for_changes()
        
        # Function moved above to fix scope issue
        
        def refresh_models(e):
            """Refresh the list of available models"""
            try:
                refresh_models_button.current.disabled = True
                page.update()
                
                url = ollama_url.current.value or "http://localhost:11434"
                available_models = get_available_models(url)
                
                # Update dropdown options
                current_value = model_dropdown.current.value
                model_dropdown.current.options = [
                    ft.dropdown.Option(model) for model in available_models
                ]
                
                # Keep current selection if it's still available, otherwise pick first
                if current_value in available_models:
                    model_dropdown.current.value = current_value
                else:
                    model_dropdown.current.value = available_models[0] if available_models else "qwen3"
                
                # Update status
                if len(available_models) > 1:
                    status_text.current.value = f"Found {len(available_models)} models: {', '.join(available_models[:3])}{'...' if len(available_models) > 3 else ''}"
                    status_text.current.color = ft.Colors.BLUE_400
                    status_icon.current.name = ft.Icons.CHECK_CIRCLE
                    status_icon.current.color = ft.Colors.BLUE_400
                else:
                    status_text.current.value = f"Found 1 model: {available_models[0] if available_models else 'None'}"
                    status_text.current.color = ft.Colors.ORANGE_400
                    status_icon.current.name = ft.Icons.WARNING
                    status_icon.current.color = ft.Colors.ORANGE_400
                    
            except Exception as ex:
                status_text.current.value = f"Error refreshing models: {str(ex)[:30]}..."
                status_text.current.color = ft.Colors.RED_400
                status_icon.current.name = ft.Icons.ERROR
                status_icon.current.color = ft.Colors.RED_400
            finally:
                refresh_models_button.current.disabled = False
                page.update()
        
        def test_agent_compatibility(e):
            """Test if the selected model supports agent/function-calling features"""
            try:
                # Update UI to show testing state
                compatibility_button.current.text = "Testing..."
                compatibility_button.current.disabled = True
                compatibility_icon.current.name = ft.Icons.REFRESH
                compatibility_icon.current.color = ft.Colors.ORANGE_400
                compatibility_text.current.value = "Testing agent compatibility..."
                compatibility_text.current.color = ft.Colors.ORANGE_400
                page.update()
                
                # Test the model's agent capabilities
                import requests
                import json
                import time
                
                url = ollama_url.current.value or "http://localhost:11434"
                model = model_dropdown.current.value or "qwen3"
                
                # Define a simple test tool
                test_tools = [{
                    "type": "function",
                    "function": {
                        "name": "get_current_time",
                        "description": "Get the current time",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                }]
                
                # Test payload with function calling
                test_payload = {
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": "What time is it? Please use the get_current_time function to find out."
                        }
                    ],
                    "tools": test_tools,
                    "stream": False
                }
                
                # Send the test request
                response = requests.post(
                    f"{url}/api/chat",
                    json=test_payload,
                    timeout=15
                )
                
                if response.status_code == 200:
                    result = response.json()
                    message = result.get('message', {})
                    
                    # Check if the model attempted to use tools
                    if 'tool_calls' in message and message['tool_calls']:
                        # Model supports function calling!
                        compatibility_icon.current.name = ft.Icons.CHECK_CIRCLE
                        compatibility_icon.current.color = ft.Colors.GREEN_400
                        compatibility_text.current.value = f"✅ Agent Compatible - {model} supports function calling"
                        compatibility_text.current.color = ft.Colors.GREEN_400
                    else:
                        # Check if model at least understood the request
                        content = message.get('content', '').lower()
                        if 'function' in content or 'tool' in content or 'time' in content:
                            # Partial understanding but no tool execution
                            compatibility_icon.current.name = ft.Icons.WARNING
                            compatibility_icon.current.color = ft.Colors.ORANGE_400
                            compatibility_text.current.value = f"⚠️ Limited Support - {model} understands tools but may not execute them"
                            compatibility_text.current.color = ft.Colors.ORANGE_400
                        else:
                            # No tool support
                            compatibility_icon.current.name = ft.Icons.ERROR
                            compatibility_icon.current.color = ft.Colors.RED_400
                            compatibility_text.current.value = f"❌ Basic Model Only - {model} doesn't support agent features"
                            compatibility_text.current.color = ft.Colors.RED_400
                else:
                    # Request failed
                    compatibility_icon.current.name = ft.Icons.ERROR
                    compatibility_icon.current.color = ft.Colors.RED_400
                    compatibility_text.current.value = f"Error testing {model} - Server responded with {response.status_code}"
                    compatibility_text.current.color = ft.Colors.RED_400
                    
            except requests.exceptions.Timeout:
                compatibility_icon.current.name = ft.Icons.ERROR
                compatibility_icon.current.color = ft.Colors.RED_400
                compatibility_text.current.value = "Compatibility test timeout - model may be too slow"
                compatibility_text.current.color = ft.Colors.RED_400
            except Exception as ex:
                compatibility_icon.current.name = ft.Icons.ERROR
                compatibility_icon.current.color = ft.Colors.RED_400
                compatibility_text.current.value = f"Test error: {str(ex)[:40]}..."
                compatibility_text.current.color = ft.Colors.RED_400
            finally:
                # Reset button state
                compatibility_button.current.text = "Test Agent Compatibility"
                compatibility_button.current.disabled = False
                page.update()
        
        def show_save_confirmation(e):
            """Show confirmation dialog for saving changes"""
            def confirm_save(e):
                # Apply the changes
                original_settings["url"] = ollama_url.current.value or "http://localhost:11434"
                original_settings["model"] = model_dropdown.current.value or original_settings["model"]
                
                # Update save button state
                check_for_changes()
                
                # Update main page model display
                if current_model_text.current:
                    current_model_text.current.value = original_settings["model"]
                    page.update()
                
                # Close dialog
                page.close(dialog)
                
                # Show success message briefly
                save_button.current.text = "Settings Saved!"
                save_button.current.style.bgcolor = ft.Colors.BLUE_600
                page.update()
                
                # Reset button text after 2 seconds
                import threading
                import time
                def reset_save_button():
                    time.sleep(2)
                    if save_button.current:
                        check_for_changes()
                threading.Thread(target=reset_save_button, daemon=True).start()
            
            def cancel_save(e):
                # Revert changes
                ollama_url.current.value = original_settings["url"]
                model_dropdown.current.value = original_settings["model"]
                
                # Update save button state
                check_for_changes()
                
                # Close dialog
                page.close(dialog)
            
            # Create confirmation dialog
            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Confirm Settings Changes"),
                content=ft.Text(
                    f"Do you want to save the following changes?\n\n"
                    f"• Ollama Server URL: {ollama_url.current.value or 'http://localhost:11434'}\n"
                    f"• Selected Model: {model_dropdown.current.value or 'qwen3'}\n\n"
                    f"These settings will be applied to your documentation generator."
                ),
                actions=[
                    ft.TextButton("Cancel", on_click=cancel_save),
                    ft.ElevatedButton(
                        "Save Changes", 
                        on_click=confirm_save,
                        style=ft.ButtonStyle(bgcolor=ft.Colors.GREEN_600)
                    ),
                ],
                actions_alignment="end",
            )
            
            page.open(dialog)
        
        def test_ollama_connection(e):
            """Test connection to Ollama server"""
            try:
                # Update UI to show testing state
                test_button.current.text = "Testing..."
                test_button.current.disabled = True
                status_icon.current.name = ft.Icons.REFRESH
                status_icon.current.color = ft.Colors.ORANGE_400
                status_text.current.value = "Testing connection..."
                status_text.current.color = ft.Colors.ORANGE_400
                page.update()
                
                # Test the connection
                import requests
                import json
                
                url = ollama_url.current.value or "http://localhost:11434"
                model = model_dropdown.current.value or "qwen3"
                
                # Test basic connectivity
                response = requests.get(f"{url}/api/tags", timeout=5)
                if response.status_code == 200:
                    # Test if the selected model is available
                    models = response.json().get('models', [])
                    model_names = [m.get('name', '').split(':')[0] for m in models]
                    
                    if model in model_names or any(model in name for name in model_names):
                        # Model is available - test a simple chat
                        test_payload = {
                            "model": model,
                            "messages": [{"role": "user", "content": "Hello"}],
                            "stream": False
                        }
                        
                        chat_response = requests.post(
                            f"{url}/api/chat", 
                            json=test_payload, 
                            timeout=10
                        )
                        
                        if chat_response.status_code == 200:
                            # Success!
                            status_icon.current.name = ft.Icons.CHECK_CIRCLE
                            status_icon.current.color = ft.Colors.GREEN_400
                            status_text.current.value = f"Connected to Ollama ({model} ready)"
                            status_text.current.color = ft.Colors.GREEN_400
                        else:
                            # Model exists but chat failed
                            status_icon.current.name = ft.Icons.WARNING
                            status_icon.current.color = ft.Colors.ORANGE_400
                            status_text.current.value = f"Connected but {model} not responding"
                            status_text.current.color = ft.Colors.ORANGE_400
                    else:
                        # Model not available
                        available_models = ", ".join(model_names[:3]) + ("..." if len(model_names) > 3 else "")
                        status_icon.current.name = ft.Icons.ERROR
                        status_icon.current.color = ft.Colors.RED_400
                        status_text.current.value = f"Model '{model}' not found. Available: {available_models}"
                        status_text.current.color = ft.Colors.RED_400
                else:
                    # Server not responding
                    status_icon.current.name = ft.Icons.ERROR
                    status_icon.current.color = ft.Colors.RED_400
                    status_text.current.value = "Cannot connect to Ollama server"
                    status_text.current.color = ft.Colors.RED_400
                    
            except requests.exceptions.Timeout:
                status_icon.current.name = ft.Icons.ERROR
                status_icon.current.color = ft.Colors.RED_400
                status_text.current.value = "Connection timeout - is Ollama running?"
                status_text.current.color = ft.Colors.RED_400
            except requests.exceptions.ConnectionError:
                status_icon.current.name = ft.Icons.ERROR
                status_icon.current.color = ft.Colors.RED_400
                status_text.current.value = "Cannot reach Ollama server"
                status_text.current.color = ft.Colors.RED_400
            except Exception as ex:
                status_icon.current.name = ft.Icons.ERROR
                status_icon.current.color = ft.Colors.RED_400
                status_text.current.value = f"Error: {str(ex)[:50]}..."
                status_text.current.color = ft.Colors.RED_400
            finally:
                # Reset button state
                test_button.current.text = "Test Connection"
                test_button.current.disabled = False
                page.update()
        
        def save_settings(e):
            """Save settings (placeholder for future implementation)"""
            # TODO: Implement settings persistence
            pass
        
        # Settings page header
        settings_header = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.IconButton(
                        icon=ft.Icons.ARROW_BACK,
                        icon_color=ft.Colors.WHITE,
                        icon_size=24,
                        tooltip="Back to Main",
                        on_click=lambda e: show_main_page(),
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.DEEP_PURPLE_600,
                            shape=ft.CircleBorder(),
                        )
                    ),
                    ft.Container(expand=True),
                    ft.Text("Settings", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ft.Container(expand=True),
                    ft.Container(width=50)  # Spacer for symmetry
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Text(
                    "Configure your documentation generator preferences",
                    size=16,
                    color=ft.Colors.GREY_400,
                    text_align=ft.TextAlign.CENTER,
                ),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.padding.symmetric(vertical=30, horizontal=20),
            bgcolor=ft.Colors.DEEP_PURPLE_800,
            border_radius=ft.border_radius.only(bottom_left=20, bottom_right=20),
            margin=ft.margin.only(bottom=30),
        )
        
        # Settings content - Ollama Configuration
        settings_content = ft.Container(
            content=ft.Column([
                ft.Text(
                    "Ollama Configuration",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color=ft.Colors.WHITE,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=20),
                
                # Ollama Settings Section
                ft.Container(
                    content=ft.Column([
                        ft.Text("Ollama Model Configuration", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ft.Container(height=15),
                        
                        # Ollama Server URL
                        ft.Row([
                            ft.Text("Ollama Server URL:", color=ft.Colors.WHITE, size=14),
                            ft.TextField(
                                ref=ollama_url,
                                value="http://localhost:11434",
                                width=200,
                                text_style=ft.TextStyle(color=ft.Colors.WHITE, size=12),
                                border_color=ft.Colors.DEEP_PURPLE_400,
                                cursor_color=ft.Colors.WHITE,
                                on_change=on_settings_change
                            )
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Container(height=10),
                        
                        # Model Selection
                        ft.Row([
                            ft.Text("Model:", color=ft.Colors.WHITE, size=14),
                            ft.Row([
                                ft.Dropdown(
                                    ref=model_dropdown,
                                    value=initial_models[0] if initial_models else "qwen3",
                                    options=[
                                        ft.dropdown.Option(model) for model in initial_models
                                    ] if initial_models else [ft.dropdown.Option("qwen3")],
                                    width=130,
                                    text_style=ft.TextStyle(color=ft.Colors.WHITE),
                                    on_change=on_settings_change
                                ),
                                ft.IconButton(
                                    ref=refresh_models_button,
                                    icon=ft.Icons.REFRESH,
                                    icon_color=ft.Colors.BLUE_400,
                                    icon_size=20,
                                    tooltip="Refresh available models",
                                    on_click=refresh_models,
                                    style=ft.ButtonStyle(
                                        bgcolor=ft.Colors.DEEP_PURPLE_700,
                                        shape=ft.CircleBorder(),
                                    )
                                )
                            ], spacing=5)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Container(height=15),
                        
                        # Agent Compatibility Test Button
                        ft.Row([
                            ft.Text("Agent Compatibility:", color=ft.Colors.WHITE, size=14),
                            ft.ElevatedButton(
                                ref=compatibility_button,
                                text="Test Agent Compatibility",
                                icon=ft.Icons.PSYCHOLOGY,
                                on_click=test_agent_compatibility,
                                style=ft.ButtonStyle(
                                    color=ft.Colors.WHITE,
                                    bgcolor=ft.Colors.PURPLE_600,
                                )
                            )
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Container(height=10),
                        
                        # Compatibility status indicator
                        ft.Row([
                            ft.Icon(ref=compatibility_icon, name=ft.Icons.CIRCLE, color=ft.Colors.GREY_400, size=12),
                            ft.Text(ref=compatibility_text, value="Click 'Test Agent Compatibility' to check if model supports function calling", color=ft.Colors.GREY_400, size=12)
                        ], spacing=8),
                        ft.Container(height=15),
                        
                        # Test Connection Button
                        ft.Row([
                            ft.Text("Connection Status:", color=ft.Colors.WHITE, size=14),
                            ft.ElevatedButton(
                                ref=test_button,
                                text="Test Connection",
                                icon=ft.Icons.WIFI_TETHERING,
                                on_click=test_ollama_connection,
                                style=ft.ButtonStyle(
                                    color=ft.Colors.WHITE,
                                    bgcolor=ft.Colors.BLUE_600,
                                )
                            )
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        ft.Container(height=10),
                        
                        # Status indicator
                        ft.Row([
                            ft.Icon(ref=status_icon, name=ft.Icons.CIRCLE, color=ft.Colors.GREY_400, size=12),
                            ft.Text(ref=status_text, value="Click 'Test Connection' to verify Ollama setup", color=ft.Colors.GREY_400, size=12)
                        ], spacing=8),
                        
                    ]),
                    padding=ft.padding.all(20),
                    bgcolor=ft.Colors.DEEP_PURPLE_900,
                    border_radius=10,
                    border=ft.border.all(1, ft.Colors.DEEP_PURPLE_600),
                    margin=ft.margin.only(bottom=20)
                ),
                
                # About Section
                ft.Container(
                    content=ft.Column([
                        ft.Text("About", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                        ft.Container(height=10),
                        ft.Text("LightningMD v1.0", color=ft.Colors.GREY_400, size=14),
                        ft.Text("AI-Powered Documentation Generator", color=ft.Colors.GREY_400, size=14),
                        ft.Text("Built with Flet + Ollama + ChromaDB", color=ft.Colors.GREY_400, size=14),
                    ]),
                    padding=ft.padding.all(20),
                    bgcolor=ft.Colors.DEEP_PURPLE_900,
                    border_radius=10,
                    border=ft.border.all(1, ft.Colors.DEEP_PURPLE_600)
                ),
                
                # Save Changes Button
                ft.Container(
                    content=ft.ElevatedButton(
                        ref=save_button,
                        text="No Changes",
                        icon=ft.Icons.SAVE,
                        disabled=True,
                        on_click=show_save_confirmation,
                        style=ft.ButtonStyle(
                            color=ft.Colors.WHITE,
                            bgcolor=ft.Colors.GREY_600,
                        ),
                        width=200
                    ),
                    alignment=ft.alignment.center,
                    margin=ft.margin.only(top=20)
                ),
            ], spacing=0, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=600,
            padding=ft.padding.all(30),
            alignment=ft.alignment.center
        )
        
        # Footer
        footer = ft.Container(
            content=ft.Text(
                "Settings are currently in development",
                italic=True,
                color=ft.Colors.GREY_400,
                size=12
            ),
            margin=ft.margin.only(top=20),
            alignment=ft.alignment.bottom_center,
        )
        
        page.add(
            ft.Column([
                settings_header,
                ft.Container(
                    content=settings_content,
                    alignment=ft.alignment.center,
                    padding=ft.padding.symmetric(horizontal=20),
                ),
                footer
            ], expand=True)
        )
    
    def show_documentation_page():
        """Switch to the documentation view page"""
        nonlocal current_view
        current_view = "documentation"
        build_documentation_page()
        page.update()
    
    # Function for documentation generation with real backend integration
    def generate_docs(e):
        # Validate input based on source type
        if source_type.value == "github":
            if not github_url.value:
                status_text.value = "❌ Please enter a GitHub URL"
                status_text.color = ft.Colors.RED_400
                status.visible = True
                page.update()
                return
            input_path = github_url.value
            source_info = f"GitHub Repository: {github_url.value}"
        else:  # folder
            if not folder_path.value:
                status_text.value = "❌ Please select a folder"
                status_text.color = ft.Colors.RED_400
                status.visible = True
                page.update()
                return
            input_path = folder_path.value
            source_info = f"Local Folder: {folder_path.value}"
        
        # Get custom prompt or use default
        custom_prompt = prompt_field.value if prompt_field.value else "Generate comprehensive documentation for this project including overview, installation, usage, and key features."
        
        # Disable the generate button during processing
        generate_button.disabled = True
        generate_button.text = "Processing..."
        page.update()
        
        # Run the processing in a separate thread to avoid blocking the UI
        def process_and_generate():
            try:
                # Step 1: Process the project (clone/validate and vectorize)
                status_text.value = "🔄 Processing project..."
                status_text.color = ft.Colors.BLUE_400
                status.visible = True
                page.update()
                
                success, message, project_path, project_name, input_type, cleanup_needed = process_project(input_path, use_temp_dir=True)
                
                if not success:
                    status_text.value = f"❌ {message}"
                    status_text.color = ft.Colors.RED_400
                    page.update()
                    return
                
                # Step 2: Vectorize the project
                status_text.value = "🧠 Creating vector database..."
                status_text.color = ft.Colors.PURPLE_400
                page.update()
                
                vector_success, vector_message, collection_name = vectorize_repository(project_path, project_name)
                
                if not vector_success:
                    status_text.value = f"❌ Vectorization failed: {vector_message}"
                    status_text.color = ft.Colors.RED_400
                    page.update()
                    return
                
                print(f"[DEBUG] Vectorization completed. Collection: {collection_name}")
                
                # Step 2.5: Verify the collection exists and is accessible
                status_text.value = "🔍 Verifying vector database..."
                page.update()
                
                # Test that we can access the collection
                try:
                    from project_setup import collection_exists
                    if not collection_exists(collection_name):
                        raise Exception(f"Collection '{collection_name}' was not created properly")
                    
                    # Test a simple search to make sure everything works
                    test_result = search_repository("test", collection_name, max_results=1)
                    print(f"[DEBUG] Collection verification successful: {len(test_result)} chars returned")
                except Exception as e:
                    status_text.value = f"❌ Vector database verification failed: {str(e)}"
                    status_text.color = ft.Colors.RED_400
                    page.update()
                    return
                
                # Step 3: Generate documentation using the agent
                status_text.value = "📝 Generating documentation with AI..."
                status_text.color = ft.Colors.GREEN_400
                page.update()
                
                print(f"[DEBUG] Starting AI agent with collection: {collection_name}")
                
                # Create a standard professional documentation prompt
                agent_prompt = f"""
                Generate COMPREHENSIVE and PROFESSIONAL markdown documentation for the project '{project_name}' in collection '{collection_name}'.

                WRITE FULL, DETAILED, AND COMPLETE DOCUMENTATION IN GREAT DETAIL.
                Make the documentation comprehensive, accurate, and professionally structured.
                Make the documentation easy to understand for average users.
                
                User request: {custom_prompt}

                IMPORTANT: Use your tools extensively (especially get_file_content()) to examine the actual codebase and extract real information, code examples, and implementation details. 
                Make the documentation comprehensive, accurate, and professionally structured.
                """
                
                print("[DEBUG] Creating messages and tools...")
                
                # Use the agent to generate documentation
                messages = [
                    {"role": "system", "content": f"You are an AI documentation agent. You have access to the '{collection_name}' collection. Use your tools to analyze and document the project."},
                    {"role": "user", "content": agent_prompt}
                ]
                
                tools = [search_repository, list_repository_collections, analyze_repository_structure, get_file_content]
                
                print("[DEBUG] Sending initial request to Ollama...")
                
                # Test Ollama connection first
                try:
                    test_response = chat(
                        model="qwen3",
                        messages=[{"role": "user", "content": "Hello, respond with just 'OK'"}],
                        stream=False
                    )
                    print(f"[DEBUG] Ollama test successful: {test_response.message.content}")
                except Exception as e:
                    raise Exception(f"Ollama connection failed: {e}")
                
                # Get response from Ollama with tools
                response = chat(
                    model="qwen3",
                    messages=messages,
                    tools=tools,
                    stream=False
                )
                
                print(f"[DEBUG] Initial response received. Has tool calls: {bool(response.message.tool_calls)}")
                print(f"[DEBUG] Response content preview: {response.message.content[:100] if response.message.content else 'No content'}...")
                
                # Execute any tool calls (with safety limits)
                max_tool_iterations = 3
                tool_iteration = 0
                
                while response.message.tool_calls and tool_iteration < max_tool_iterations:
                    tool_iteration += 1
                    print(f"[DEBUG] Tool execution round {tool_iteration}/{max_tool_iterations}")
                    
                    for i, call in enumerate(response.message.tool_calls):
                        fn_name = call.function.name
                        args = call.function.arguments or {}
                        
                        print(f"[DEBUG] Executing tool {i+1}/{len(response.message.tool_calls)}: {fn_name} with args: {args}")
                        
                        try:
                            # Execute the tool with timeout protection
                            if fn_name == "search_repository":
                                result = search_repository(**args)
                            elif fn_name == "list_repository_collections":
                                result = list_repository_collections(**args)
                            elif fn_name == "analyze_repository_structure":
                                result = analyze_repository_structure(**args)
                            elif fn_name == "get_file_content":
                                result = get_file_content(**args)
                            else:
                                result = f"Unknown tool: {fn_name}"
                            
                            print(f"[DEBUG] Tool {fn_name} completed. Result length: {len(str(result))} chars")
                            
                        except Exception as e:
                            result = f"Error executing {fn_name}: {str(e)}"
                            print(f"[DEBUG] Tool {fn_name} failed: {e}")
                        
                        messages.append({
                            "role": "tool",
                            "name": fn_name,
                            "content": result
                        })
                    
                    print(f"[DEBUG] Getting next response from Ollama...")
                    
                    # Get next response
                    try:
                        response = chat(
                            model="qwen3",
                            messages=messages,
                            tools=tools,
                            stream=False
                        )
                        print(f"[DEBUG] Next response received. Has more tool calls: {bool(response.message.tool_calls)}")
                    except Exception as e:
                        print(f"[DEBUG] Error getting next response: {e}")
                        raise e
                
                if tool_iteration >= max_tool_iterations:
                    print(f"[DEBUG] Reached maximum tool iterations ({max_tool_iterations}), proceeding with current response")
                
                # Get final documentation
                final_response = chat(
                    model="qwen3",
                    messages=messages
                )
                
                documentation = final_response.message.content
                
                # Step 4: Store documentation and navigate to documentation page
                status_text.value = "✅ Documentation generated successfully!"
                status_text.color = ft.Colors.GREEN_400
                progress_bar.visible = False  # Hide progress bar when complete
                page.update()
                
                # Clean and store the generated documentation and project info
                nonlocal generated_documentation, project_info
                generated_documentation = clean_documentation(documentation)
                project_info = {
                    'name': project_name,
                    'type': input_type,
                    'path': input_path
                }
                
                # Show the view documentation button for future use
                view_docs_button.visible = True
                
                # Wait a moment then navigate to documentation page
                time.sleep(1)
                show_documentation_page()
                
                # Cleanup if needed
                if cleanup_needed and project_path:
                    try:
                        from project_setup import cleanup_repository
                        cleanup_repository(project_path)
                    except:
                        pass  # Silent cleanup failure
                        
            except Exception as e:
                status_text.value = f"❌ Error: {str(e)}"
                status_text.color = ft.Colors.RED_400
                page.update()
            
            finally:
                # Re-enable the generate button
                generate_button.disabled = False
                generate_button.text = "Generate Documentation"
                page.update()
        
        # Start processing in a separate thread
        threading.Thread(target=process_and_generate, daemon=True).start()
    
    def build_main_page():
        """Build and display the main page"""
        page.controls.clear()
        page.add(main_page_content)
    
    def build_documentation_page():
        """Build and display the documentation page"""
        page.controls.clear()
        
        # Debug: Print documentation content
        print(f"[DEBUG] Building documentation page...")
        print(f"[DEBUG] Documentation length: {len(generated_documentation)} chars")
        print(f"[DEBUG] Documentation preview: {generated_documentation[:200]}..." if generated_documentation else "[DEBUG] No documentation available")
        
        # Documentation page header
        doc_header = ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.IconButton(
                        icon=ft.Icons.ARROW_BACK,
                        icon_color=ft.Colors.WHITE,
                        icon_size=24,
                        on_click=lambda e: show_main_page(),
                        tooltip="Back to Main Page"
                    ),
                    ft.Text("Generated Documentation", size=28, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ], alignment=ft.MainAxisAlignment.START, spacing=15),
                ft.Text(
                    f"Project: {project_info.get('name', 'Unknown')} ({project_info.get('type', 'Unknown')})",
                    size=14,
                    color=ft.Colors.GREY_400,
                ),
            ]),
            padding=ft.padding.all(20),
            bgcolor=ft.Colors.DEEP_PURPLE_800,
            border_radius=ft.border_radius.only(bottom_left=20, bottom_right=20),
            margin=ft.margin.only(bottom=20),
        )
        
        # Documentation content with markdown rendering (with fallback)
        try:
            # Try markdown rendering first
            doc_display = ft.Markdown(
                value=generated_documentation if generated_documentation else "No documentation available",
                extension_set=ft.MarkdownExtensionSet.GITHUB_FLAVORED,
                code_theme=ft.MarkdownCodeTheme.ATOM_ONE_DARK,
                expand=True
            )
            print("[DEBUG] Using Markdown component")
        except Exception as e:
            print(f"[DEBUG] Markdown failed, using TextField fallback: {e}")
            # Fallback to TextField if Markdown fails
            doc_display = ft.TextField(
                value=generated_documentation if generated_documentation else "No documentation available",
                multiline=True,
                read_only=True,
                text_style=ft.TextStyle(color=ft.Colors.WHITE, size=14),
                bgcolor=ft.Colors.TRANSPARENT,
                border=ft.InputBorder.NONE,
                expand=True
            )
        
        doc_content = ft.Container(
            content=ft.Column([
                doc_display
            ], scroll=ft.ScrollMode.AUTO, expand=True),
            padding=ft.padding.all(20),
            bgcolor=ft.Colors.GREY_900,
            border=ft.border.all(1, ft.Colors.DEEP_PURPLE_600),
            border_radius=10,
            expand=True
        )
        
        # Download function
        def download_documentation(e):
            """Download documentation as README.md file"""
            if not generated_documentation:
                return
            
            # Create file picker for save location
            def save_file(file_picker_result):
                if file_picker_result.path:
                    try:
                        # Ensure the file has .md extension
                        file_path = file_picker_result.path
                        if not file_path.endswith('.md'):
                            file_path += '.md'
                        
                        # Write documentation to file
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(generated_documentation)
                        
                        # Show success message
                        download_btn.text = "Downloaded!"
                        download_btn.icon = ft.Icons.CHECK
                        page.update()
                        
                        # Reset button after 2 seconds
                        def reset_download_button():
                            import time
                            time.sleep(2)
                            download_btn.text = "Download README.md"
                            download_btn.icon = ft.Icons.DOWNLOAD
                            page.update()
                        
                        import threading
                        threading.Thread(target=reset_download_button, daemon=True).start()
                        
                    except Exception as ex:
                        print(f"Error saving file: {ex}")
            
            # Create and open file picker
            file_picker = ft.FilePicker(on_result=save_file)
            page.overlay.append(file_picker)
            page.update()
            file_picker.save_file(
                dialog_title="Save Documentation as README.md",
                file_name="README.md",
                allowed_extensions=["md"]
            )
        
        # Copy and Download buttons
        copy_btn = ft.ElevatedButton(
            "Copy Documentation",
            icon=ft.Icons.COPY,
            on_click=lambda e: page.set_clipboard(generated_documentation),
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.GREEN_600,
                elevation=4,
                shape=ft.RoundedRectangleBorder(radius=10),
            ),
        )
        
        download_btn = ft.ElevatedButton(
            "Download README.md",
            icon=ft.Icons.DOWNLOAD,
            on_click=download_documentation,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_600,
                elevation=4,
                shape=ft.RoundedRectangleBorder(radius=10),
            ),
        )
        
        buttons_row = ft.Container(
            content=ft.Row([
                copy_btn,
                download_btn
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=20),
            padding=ft.padding.all(20),
            alignment=ft.alignment.center
        )
        
        page.add(
            ft.Column([
                doc_header,
                doc_content,
                buttons_row
            ], expand=True)
        )
    
    # Current model display reference
    current_model_text = ft.Ref[ft.Text]()
    
    def get_current_model():
        """Get the current model from settings or default"""
        try:
            # Try to get from settings page if it exists
            # For now, return default but this will be connected to actual settings
            return "qwen3"  # Default for now, will be updated by settings page
        except:
            return "qwen3"  # Fallback
    
    def update_current_model_display():
        """Update the current model display in the header"""
        if current_model_text.current:
            current_model_text.current.value = get_current_model()
            page.update()
    
    # Refresh function
    def refresh_interface(e):
        """Reset the interface to initial state"""
        # Clear all inputs
        github_url.value = ""
        folder_path.value = "Selected folder path"
        prompt_field.value = "Generate a comprehensive README with installation instructions and examples."
        
        # Reset radio button to GitHub
        source_type.value = "github"
        
        # Hide status and documentation areas
        status.visible = False
        view_docs_button.visible = False
        
        # Clear any generated documentation
        nonlocal generated_documentation, project_info
        generated_documentation = ""
        project_info = {}
        
        # Update visibility based on source type
        github_url.visible = True
        folder_path.visible = False
        folder_picker_button.visible = False
        
        # Reset to main page if on documentation page
        nonlocal current_view
        if current_view == "documentation":
            show_main_page()
        
        page.update()
    
    # Header with logo/title and refresh button
    header = ft.Container(
        content=ft.Column([
            # Top row with title, settings, and refresh buttons
            ft.Row([
                ft.Icon(ft.Icons.BOLT, size=48, color=ft.Colors.YELLOW),
                ft.Text("LightningMD", size=36, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                ft.Container(expand=True),  # Spacer to push buttons to the right
                ft.IconButton(
                    icon=ft.Icons.SETTINGS,
                    icon_color=ft.Colors.WHITE,
                    icon_size=24,
                    tooltip="Settings",
                    on_click=lambda e: show_settings_page(),
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.DEEP_PURPLE_600,
                        shape=ft.CircleBorder(),
                    )
                ),
                ft.IconButton(
                    icon=ft.Icons.REFRESH,
                    icon_color=ft.Colors.WHITE,
                    icon_size=24,
                    tooltip="Refresh Interface",
                    on_click=refresh_interface,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.DEEP_PURPLE_600,
                        shape=ft.CircleBorder(),
                    )
                )
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=15),
            ft.Text(
                "AI-Powered Documentation Generator",
                size=16,
                color=ft.Colors.GREY_400,
                text_align=ft.TextAlign.CENTER,
            ),
            # Current model display
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.SMART_TOY, size=16, color=ft.Colors.PURPLE_300),
                    ft.Text(
                        "Current Model: ",
                        size=12,
                        color=ft.Colors.PURPLE_300,
                        weight=ft.FontWeight.W_500
                    ),
                    ft.Text(
                        ref=current_model_text,
                        value=get_current_model(),
                        size=12,
                        color=ft.Colors.WHITE,
                        weight=ft.FontWeight.BOLD
                    ),
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=5),
                margin=ft.margin.only(top=10),
                padding=ft.padding.symmetric(horizontal=15, vertical=8),
                bgcolor=ft.Colors.DEEP_PURPLE_700,
                border_radius=15,
                border=ft.border.all(1, ft.Colors.PURPLE_400),
            ),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        padding=ft.padding.symmetric(vertical=40, horizontal=20),
        bgcolor=ft.Colors.DEEP_PURPLE_800,
        border_radius=ft.border_radius.only(bottom_left=20, bottom_right=20),
        margin=ft.margin.only(bottom=30),
    )
    
    # Source selection radio buttons
    source_type = ft.RadioGroup(
        content=ft.Row([
            ft.Radio(value="github", label="GitHub Repository", label_style=ft.TextStyle(color=ft.Colors.WHITE)),
            ft.Radio(value="folder", label="Local Folder", label_style=ft.TextStyle(color=ft.Colors.WHITE)),
        ], spacing=30),
        value="github"
    )
    
    # GitHub URL input
    github_url = ft.TextField(
        label="GitHub Repository URL",
        hint_text="https://github.com/username/repository",
        width=600,
        prefix_icon=ft.Icons.LINK,
        visible=True,
        bgcolor=ft.Colors.DEEP_PURPLE_900,
        border_color=ft.Colors.DEEP_PURPLE_600,
        focused_border_color=ft.Colors.PURPLE_400,
        label_style=ft.TextStyle(color=ft.Colors.PURPLE_200),
        text_style=ft.TextStyle(color=ft.Colors.WHITE),
        hint_style=ft.TextStyle(color=ft.Colors.PURPLE_300),
        border_radius=10,
    )
    
    # Folder path display and picker
    folder_path = ft.TextField(
        label="Selected Folder Path",
        hint_text="No folder selected",
        width=500,
        read_only=True,
        visible=False,
        bgcolor=ft.Colors.DEEP_PURPLE_900,
        border_color=ft.Colors.DEEP_PURPLE_600,
        label_style=ft.TextStyle(color=ft.Colors.PURPLE_200),
        text_style=ft.TextStyle(color=ft.Colors.WHITE),
        hint_style=ft.TextStyle(color=ft.Colors.PURPLE_300),
        border_radius=10,
    )
    
    # Create FilePicker for folder selection
    def folder_picker_result(e: ft.FilePickerResultEvent):
        if e.path:
            folder_path.value = e.path
            folder_path.update()
    
    folder_picker = ft.FilePicker(on_result=folder_picker_result)
    page.overlay.append(folder_picker)
    
    def pick_folder(e):
        folder_picker.get_directory_path()
    
    folder_picker_button = ft.ElevatedButton(
        "Browse Folder",
        icon=ft.Icons.FOLDER_OPEN,
        on_click=pick_folder,
        visible=False,
        width=150,
        height=40,
        style=ft.ButtonStyle(
            color=ft.Colors.WHITE,
            bgcolor=ft.Colors.DEEP_PURPLE_700,
            overlay_color=ft.Colors.DEEP_PURPLE_600,
            elevation=4,
            shape=ft.RoundedRectangleBorder(radius=10),
            text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_500),
        ),
    )
    
    # Function to handle source type changes
    def source_type_changed(e):
        if source_type.value == "github":
            github_url.visible = True
            folder_path.visible = False
            folder_picker_button.visible = False
        else:
            github_url.visible = False
            folder_path.visible = True
            folder_picker_button.visible = True
        page.update()
    
    source_type.on_change = source_type_changed
    
    # Prompt input for customizing documentation generation
    prompt_field = ft.TextField(
        label="Documentation Prompt (Optional)",
        hint_text="e.g., 'Generate a comprehensive README with installation instructions and examples'",
        width=600,
        multiline=True,
        min_lines=2,
        max_lines=4,
        prefix_icon=ft.Icons.EDIT_NOTE,
        bgcolor=ft.Colors.DEEP_PURPLE_900,
        border_color=ft.Colors.DEEP_PURPLE_600,
        focused_border_color=ft.Colors.PURPLE_400,
        label_style=ft.TextStyle(color=ft.Colors.PURPLE_200),
        text_style=ft.TextStyle(color=ft.Colors.WHITE),
        hint_style=ft.TextStyle(color=ft.Colors.PURPLE_300),
        border_radius=10,
    )
    
    # Generate button
    generate_button = ft.ElevatedButton(
        "Generate Documentation",
        icon=ft.Icons.DOCUMENT_SCANNER,
        on_click=generate_docs,
        width=200,
        height=50,
        style=ft.ButtonStyle(
            color=ft.Colors.WHITE,
            bgcolor=ft.Colors.BLUE_600,
            overlay_color=ft.Colors.BLUE_700,
            elevation=8,
            shadow_color=ft.Colors.BLUE_900,
            shape=ft.RoundedRectangleBorder(radius=12),
            text_style=ft.TextStyle(size=16, weight=ft.FontWeight.BOLD),
        ),
    )
    
    # View documentation button (initially hidden)
    view_docs_button = ft.ElevatedButton(
        "View Last Documentation",
        icon=ft.Icons.DESCRIPTION,
        on_click=lambda e: show_documentation_page(),
        width=200,
        height=50,
        visible=False,
        style=ft.ButtonStyle(
            color=ft.Colors.WHITE,
            bgcolor=ft.Colors.GREEN_600,
            overlay_color=ft.Colors.GREEN_700,
            elevation=8,
            shadow_color=ft.Colors.GREEN_900,
            shape=ft.RoundedRectangleBorder(radius=12),
            text_style=ft.TextStyle(size=16, weight=ft.FontWeight.BOLD),
        ),
    )
    
    # Status area (initially hidden)
    status_text = ft.Text(size=16, color=ft.Colors.BLUE_400)
    progress_bar = ft.ProgressBar(width=600, color=ft.Colors.BLUE_400)
    
    status = ft.Container(
        content=ft.Column([
            ft.Text("Status:", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER),
            status_text,
            progress_bar
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        visible=False,
        margin=ft.margin.only(top=20, bottom=20),
        padding=ft.padding.all(15),
        bgcolor=ft.Colors.DEEP_PURPLE_900,
        border_radius=10,
        border=ft.border.all(1, ft.Colors.DEEP_PURPLE_600),
        alignment=ft.alignment.center
    )
    
    # Documentation display area (initially hidden) - Enhanced with better styling
    documentation_content = ft.Container(
        content=ft.Column(
            scroll=ft.ScrollMode.AUTO,
            spacing=0
        ),
        width=600,
        height=400,
        bgcolor=ft.Colors.GREY_900,
        border=ft.border.all(1, ft.Colors.DEEP_PURPLE_600),
        border_radius=10,
        padding=ft.padding.all(20)
    )
    
    def format_documentation(text):
        """Format the documentation text into visually appealing components"""
        if not text:
            return []
        
        components = []
        lines = text.split('\n')
        current_section = []
        
        for line in lines:
            line = line.strip()
            
            # Handle headers (lines starting with # or ##)
            if line.startswith('##'):
                if current_section:
                    components.append(ft.Text('\n'.join(current_section), 
                                            color=ft.Colors.WHITE, 
                                            size=14, 
                                            selectable=True))
                    current_section = []
                components.append(ft.Text(line.replace('##', '').strip(), 
                                        color=ft.Colors.PURPLE_300, 
                                        size=18, 
                                        weight=ft.FontWeight.BOLD))
                components.append(ft.Container(height=10))  # Spacing
            elif line.startswith('#'):
                if current_section:
                    components.append(ft.Text('\n'.join(current_section), 
                                            color=ft.Colors.WHITE, 
                                            size=14, 
                                            selectable=True))
                    current_section = []
                components.append(ft.Text(line.replace('#', '').strip(), 
                                        color=ft.Colors.BLUE_300, 
                                        size=20, 
                                        weight=ft.FontWeight.BOLD))
                components.append(ft.Container(height=15))  # Spacing
            # Handle bullet points
            elif line.startswith('-') or line.startswith('*'):
                if current_section:
                    components.append(ft.Text('\n'.join(current_section), 
                                            color=ft.Colors.WHITE, 
                                            size=14, 
                                            selectable=True))
                    current_section = []
                components.append(ft.Row([
                    ft.Text('•', color=ft.Colors.PURPLE_400, size=16, weight=ft.FontWeight.BOLD),
                    ft.Text(line[1:].strip(), color=ft.Colors.WHITE, size=14, selectable=True)
                ], spacing=10))
            # Handle numbered lists
            elif line and line[0].isdigit() and '.' in line[:5]:
                if current_section:
                    components.append(ft.Text('\n'.join(current_section), 
                                            color=ft.Colors.WHITE, 
                                            size=14, 
                                            selectable=True))
                    current_section = []
                components.append(ft.Text(line, color=ft.Colors.GREEN_300, size=14, weight=ft.FontWeight.W_500, selectable=True))
            # Handle code blocks or special formatting
            elif line.startswith('```') or line.startswith('`'):
                if current_section:
                    components.append(ft.Text('\n'.join(current_section), 
                                            color=ft.Colors.WHITE, 
                                            size=14, 
                                            selectable=True))
                    current_section = []
                components.append(ft.Container(
                    content=ft.Text(line.replace('`', ''), 
                                   color=ft.Colors.YELLOW_300, 
                                   size=13, 
                                   font_family='Courier New',
                                   selectable=True),
                    bgcolor=ft.Colors.GREY_800,
                    padding=ft.padding.all(10),
                    border_radius=5,
                    margin=ft.margin.symmetric(vertical=5)
                ))
            # Regular text
            elif line:
                current_section.append(line)
            # Empty line - add spacing
            else:
                if current_section:
                    components.append(ft.Text('\n'.join(current_section), 
                                            color=ft.Colors.WHITE, 
                                            size=14, 
                                            selectable=True))
                    current_section = []
                components.append(ft.Container(height=10))
        
        # Add remaining content
        if current_section:
            components.append(ft.Text('\n'.join(current_section), 
                                    color=ft.Colors.WHITE, 
                                    size=14, 
                                    selectable=True))
        
        return components
    
    # Store the raw documentation text for copying
    raw_documentation_text = ""
    
    def copy_documentation(e):
        if raw_documentation_text:
            page.set_clipboard(raw_documentation_text)
            # Show a brief success message
            copy_button.text = "Copied!"
            copy_button.icon = ft.Icons.CHECK
            page.update()
            
            # Reset button after 2 seconds
            def reset_button():
                time.sleep(2)
                copy_button.text = "Copy Documentation"
                copy_button.icon = ft.Icons.COPY
                page.update()
            
            threading.Thread(target=reset_button, daemon=True).start()
    
    copy_button = ft.ElevatedButton(
        "Copy Documentation",
        icon=ft.Icons.COPY,
        on_click=copy_documentation,
        width=180,
        height=40,
        style=ft.ButtonStyle(
            color=ft.Colors.WHITE,
            bgcolor=ft.Colors.GREEN_600,
            overlay_color=ft.Colors.GREEN_700,
            elevation=4,
            shape=ft.RoundedRectangleBorder(radius=10),
            text_style=ft.TextStyle(size=14, weight=ft.FontWeight.W_500),
        ),
    )
    
    documentation_area = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("Generated Documentation:", weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE, size=18),
                copy_button
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Container(height=10),  # Spacing
            documentation_content
        ]),
        visible=False,
        margin=ft.margin.only(top=20),
        padding=ft.padding.all(15),
        bgcolor=ft.Colors.DEEP_PURPLE_900,
        border_radius=10,
        border=ft.border.all(1, ft.Colors.DEEP_PURPLE_600)
    )
    
    # Footer
    footer = ft.Container(
        content=ft.Text(
            "Powered by Flet + Ollama (quen3)",
            italic=True,
            color=ft.Colors.GREY_400,
            size=12
        ),
        margin=ft.margin.only(top=20),
        alignment=ft.alignment.bottom_center,
    )
    
    # Main content container
    main_content = ft.Container(
        content=ft.Column([
            ft.Text(
                "Choose your source and customize your documentation prompt",
                size=18,
                color=ft.Colors.WHITE,
                text_align=ft.TextAlign.CENTER,
                weight=ft.FontWeight.W_500,
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text(
                        "Select Source Type:",
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.WHITE,
                        size=16,
                    ),
                    source_type,
                ], spacing=10),
                margin=ft.margin.only(bottom=20),
                padding=ft.padding.all(20),
                bgcolor=ft.Colors.DEEP_PURPLE_800,
                border_radius=15,
                border=ft.border.all(1, ft.Colors.DEEP_PURPLE_700),
            ),
            github_url,
            folder_path,
            ft.Row([
                folder_picker_button,
            ], alignment=ft.MainAxisAlignment.CENTER),
            prompt_field,
            ft.Container(
                content=ft.Row([
                    generate_button,
                    view_docs_button,
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=20),
                alignment=ft.alignment.center,
                margin=ft.margin.only(top=20),
            ),
        ], spacing=20, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        width=700,
        padding=ft.padding.all(30),
        bgcolor=ft.Colors.DEEP_PURPLE_800,
        border_radius=20,
        border=ft.border.all(1, ft.Colors.DEEP_PURPLE_700),
        shadow=ft.BoxShadow(
            spread_radius=1,
            blur_radius=15,
            color=ft.Colors.BLACK26,
            offset=ft.Offset(0, 4),
        ),
    )
    
    # Create main page content container
    main_page_content = ft.Column([
        header,
        ft.Container(
            content=main_content,
            alignment=ft.alignment.center,
            padding=ft.padding.symmetric(horizontal=20),
        ),
        status,
        footer
    ])
    
    # Navigation functions with state management (defined after main_page_content)
    def show_main_page():
        """Show the main page"""
        if current_page_state["current"] == "main":
            return  # Already on main page, prevent duplication
        
        current_page_state["current"] = "main"
        page.controls.clear()
        page.controls.append(main_page_content)
        page.update()
    
    def show_documentation_page():
        """Show the documentation page"""
        if current_page_state["current"] == "documentation":
            return  # Already on documentation page, prevent duplication
        
        current_page_state["current"] = "documentation"
        build_documentation_page()
    
    def show_settings_page():
        """Show the settings page"""
        build_settings_page()
    
    # Initialize with main page using proper Flet pattern
    page.add(main_page_content)

ft.app(main)
