#!/usr/bin/env python3
"""
Simple script to clone any GitHub repository given a URL.
This script provides functionality to clone repositories and handle common scenarios.
"""

import os
import sys
import subprocess
import shutil
import tempfile
import atexit
from urllib.parse import urlparse
from pathlib import Path
import chromadb
import tiktoken
import mimetypes

def validate_github_url(url):
    """
    Validate if the provided URL is a valid GitHub repository URL.
    
    Args:
        url (str): The GitHub repository URL
        
    Returns:
        bool: True if valid GitHub URL, False otherwise
    """
    try:
        parsed = urlparse(url)
        if parsed.netloc.lower() not in ['github.com', 'www.github.com']:
            return False
        
        # Check if path has at least owner/repo format
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) < 2:
            return False
            
        return True
    except Exception:
        return False

def validate_local_folder(folder_path):
    """
    Validate if the provided path is a valid local project folder.
    
    Args:
        folder_path (str): The local folder path
        
    Returns:
        bool: True if valid local folder, False otherwise
    """
    try:
        # Normalize the path to handle different path formats and special characters
        normalized_path = os.path.normpath(os.path.expanduser(folder_path))
        
        # Check if path exists and is a directory
        if not os.path.exists(normalized_path):
            return False
        
        if not os.path.isdir(normalized_path):
            return False
        
        # Check if directory is readable
        if not os.access(normalized_path, os.R_OK):
            return False
        
        # Check if directory has at least one file (not empty)
        try:
            # Use os.listdir instead of os.walk for better error handling
            contents = os.listdir(normalized_path)
            return len(contents) > 0
        except (OSError, PermissionError):
            return False  # Cannot read directory contents
            
    except Exception:
        return False

def detect_input_type(input_path):
    """
    Detect whether the input is a GitHub URL or a local folder path.
    
    Args:
        input_path (str): The input path or URL
        
    Returns:
        str: 'github' if GitHub URL, 'local' if local folder, 'invalid' if neither
    """
    if validate_github_url(input_path):
        return 'github'
    elif validate_local_folder(input_path):
        return 'local'
    else:
        return 'invalid'

def get_project_name(input_path, input_type):
    """
    Extract project name from either GitHub URL or local folder path.
    
    Args:
        input_path (str): The input path or URL
        input_type (str): Type of input ('github' or 'local')
        
    Returns:
        str: Project name
    """
    if input_type == 'github':
        return extract_repo_name(input_path)
    elif input_type == 'local':
        # Normalize path and extract basename
        normalized_path = os.path.normpath(os.path.expanduser(input_path))
        project_name = os.path.basename(normalized_path)
        
        # Clean up the project name for use as collection name
        # Replace spaces and special characters with underscores
        import re
        clean_name = re.sub(r'[^a-zA-Z0-9_-]', '_', project_name)
        clean_name = re.sub(r'_+', '_', clean_name)  # Replace multiple underscores with single
        clean_name = clean_name.strip('_')  # Remove leading/trailing underscores
        
        return clean_name if clean_name else 'local_project'
    else:
        return 'unknown_project'

def extract_repo_name(url):
    """
    Extract repository name from GitHub URL.
    
    Args:
        url (str): The GitHub repository URL
        
    Returns:
        str: Repository name
    """
    parsed = urlparse(url)
    path_parts = parsed.path.strip('/').split('/')
    repo_name = path_parts[1]
    
    # Remove .git extension if present
    if repo_name.endswith('.git'):
        repo_name = repo_name[:-4]
        
    return repo_name

def clone_repository(github_url, use_temp_dir=True):
    """
    Clone a GitHub repository to a temporary directory.
    
    Args:
        github_url (str): The GitHub repository URL
        use_temp_dir (bool): If True, uses a temporary directory. If False, uses current directory.
        
    Returns:
        tuple: (success: bool, message: str, cloned_path: str)
    """
    try:
        # Validate the GitHub URL
        if not validate_github_url(github_url):
            return False, "Invalid GitHub URL provided", None
        
        # Extract repository name
        repo_name = extract_repo_name(github_url)
        
        # Determine target directory
        if use_temp_dir:
            # Create a temporary directory
            temp_base = tempfile.mkdtemp(prefix=f"lightningmd_{repo_name}_")
            target_dir = os.path.join(temp_base, repo_name)
            
            # Register cleanup function to remove temp directory on exit
            def cleanup_temp():
                try:
                    if os.path.exists(temp_base):
                        # Handle Windows file permission issues with Git repositories
                        def handle_remove_readonly(func, path, exc):
                            import stat
                            os.chmod(path, stat.S_IWRITE)
                            func(path)
                        
                        shutil.rmtree(temp_base, onerror=handle_remove_readonly)
                        print(f"Cleaned up temporary directory: {temp_base}")
                except Exception as e:
                    print(f"Warning: Could not clean up temp directory: {e}")
                    # Try force removal as last resort
                    try:
                        subprocess.run(['rmdir', '/s', '/q', temp_base], shell=True, check=False)
                    except:
                        pass
            
            atexit.register(cleanup_temp)
        else:
            # Use current directory (fallback for testing)
            target_dir = os.path.join(os.getcwd(), repo_name)
            
            # Check if directory already exists
            if os.path.exists(target_dir):
                return False, f"Directory '{target_dir}' already exists", None
        
        # Clone the repository
        print(f"Cloning {github_url} to temporary directory...")
        result = subprocess.run(
            ['git', 'clone', github_url, target_dir],
            capture_output=True,
            text=True,
            check=True
        )
        
        return True, f"Successfully cloned repository to {target_dir}", target_dir
        
    except subprocess.CalledProcessError as e:
        error_msg = f"Git clone failed: {e.stderr.strip() if e.stderr else str(e)}"
        return False, error_msg, None
    except Exception as e:
        return False, f"Unexpected error: {str(e)}", None

def is_text_file(file_path):
    """
    Check if a file is a text file that should be processed.
    
    Args:
        file_path (str): Path to the file
        
    Returns:
        bool: True if file should be processed, False otherwise
    """
    # Skip binary and unwanted files
    skip_extensions = {
        '.pyc', '.pyo', '.pyd', '.so', '.dll', '.dylib',
        '.exe', '.bin', '.obj', '.o', '.a', '.lib',
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico',
        '.mp3', '.mp4', '.avi', '.mov', '.wav', '.pdf',
        '.zip', '.tar', '.gz', '.rar', '.7z'
    }
    
    # Skip hidden files and directories
    if os.path.basename(file_path).startswith('.'):
        return False
    
    # Check extension
    _, ext = os.path.splitext(file_path.lower())
    if ext in skip_extensions:
        return False
    
    # Try to detect if it's a text file
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            # Read first 1024 bytes to check if it's text
            sample = f.read(1024)
            # If we can read it and it doesn't contain too many null bytes, it's probably text
            null_ratio = sample.count('\0') / len(sample) if sample else 0
            return null_ratio < 0.1
    except:
        return False

def chunk_text(text, max_tokens=500):
    """
    Split text into chunks based on token count.
    
    Args:
        text (str): Text to chunk
        max_tokens (int): Maximum tokens per chunk
        
    Returns:
        list: List of text chunks
    """
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        tokens = encoding.encode(text)
        
        chunks = []
        for i in range(0, len(tokens), max_tokens):
            chunk_tokens = tokens[i:i + max_tokens]
            chunk_text = encoding.decode(chunk_tokens)
            chunks.append(chunk_text)
        
        return chunks
    except Exception:
        # Fallback: split by characters if tiktoken fails
        chunk_size = max_tokens * 4  # Rough estimate: 4 chars per token
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

def vectorize_repository(repo_path, repo_name):
    """
    Create a ChromaDB vector database from the repository files.
    
    Args:
        repo_path (str): Path to the cloned repository
        repo_name (str): Name of the repository
        
    Returns:
        tuple: (success: bool, message: str, collection_name: str)
    """
    try:
        print(f"🔍 Analyzing repository structure...")
        
        # Initialize ChromaDB persistent client with absolute path
        script_dir = os.path.dirname(os.path.abspath(__file__))
        chroma_db_path = os.path.join(script_dir, "chroma_db")
        
        client = chromadb.PersistentClient(path=chroma_db_path)
        
        # Create or get collection
        collection_name = f"repo_{repo_name.replace('-', '_').replace('.', '_')}"
        
        # Check if collection already exists
        if collection_exists(collection_name):
            print(f"⚠️  Collection '{collection_name}' already exists!")
            print(f"   This repository has been vectorized before.")
            print(f"   Deleting existing collection and creating fresh vectors...")
            client.delete_collection(collection_name)
        else:
            print(f"📦 Creating new collection: '{collection_name}'")
        
        collection = client.create_collection(
            name=collection_name,
            metadata={"repo_name": repo_name, "created_at": str(os.path.getctime(repo_path))}
        )
        
        documents = []
        metadatas = []
        ids = []
        
        file_count = 0
        processed_count = 0
        
        print(f"📁 Processing files...")
        
        # Walk through all files in the repository
        for root, dirs, files in os.walk(repo_path):
            # Skip .git directory
            if '.git' in dirs:
                dirs.remove('.git')
            
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, repo_path)
                
                file_count += 1
                
                # Skip if not a text file
                if not is_text_file(file_path):
                    continue
                
                try:
                    # Read file content
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    if not content.strip():
                        continue
                    
                    # Chunk the content
                    chunks = chunk_text(content, max_tokens=500)
                    
                    for i, chunk in enumerate(chunks):
                        if not chunk.strip():
                            continue
                        
                        doc_id = f"{relative_path}_chunk_{i}"
                        
                        documents.append(chunk)
                        metadatas.append({
                            "file_path": relative_path,
                            "chunk_index": i,
                            "file_type": os.path.splitext(file)[1],
                            "file_size": len(content)
                        })
                        ids.append(doc_id)
                    
                    processed_count += 1
                    
                    if processed_count % 10 == 0:
                        print(f"   Processed {processed_count} files...")
                        
                except Exception as e:
                    print(f"   Warning: Could not process {relative_path}: {e}")
                    continue
        
        if not documents:
            return False, "No processable text files found in repository", None
        
        print(f"💾 Creating vector embeddings for {len(documents)} chunks...")
        
        # Add documents to ChromaDB in batches
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i + batch_size]
            batch_metas = metadatas[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]
            
            collection.add(
                documents=batch_docs,
                metadatas=batch_metas,
                ids=batch_ids
            )
            
            print(f"   Added batch {i//batch_size + 1}/{(len(documents) + batch_size - 1)//batch_size}")
        
        success_msg = (
            f"Successfully vectorized repository:\n"
            f"  📊 Total files scanned: {file_count}\n"
            f"  📝 Text files processed: {processed_count}\n"
            f"  🧩 Document chunks created: {len(documents)}\n"
            f"  🗃️  Collection name: {collection_name}"
        )
        
        return True, success_msg, collection_name
        
    except Exception as e:
        return False, f"Failed to vectorize repository: {str(e)}", None

def list_vector_databases():
    """
    List all available vector database collections.
    
    Returns:
        list: List of collection names and metadata
    """
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        chroma_db_path = os.path.join(script_dir, "chroma_db")
        
        if not os.path.exists(chroma_db_path):
            return []
        
        client = chromadb.PersistentClient(path=chroma_db_path)
        
        collections = client.list_collections()
        return [(col.name, col.metadata) for col in collections]
    except Exception as e:
        print(f"Warning: Could not list vector databases: {e}")
        return []

def delete_vector_database(collection_name):
    """
    Delete a specific vector database collection.
    
    Args:
        collection_name (str): Name of the collection to delete
        
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        chroma_db_path = os.path.join(script_dir, "chroma_db")
        
        client = chromadb.PersistentClient(path=chroma_db_path)
        
        client.delete_collection(collection_name)
        return True, f"Successfully deleted collection '{collection_name}'"
    except Exception as e:
        return False, f"Failed to delete collection: {str(e)}"

def cleanup_all_vector_databases():
    """
    Remove all vector database collections and the chroma_db directory.
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        chroma_db_path = os.path.join(script_dir, "chroma_db")
        
        if os.path.exists(chroma_db_path):
            shutil.rmtree(chroma_db_path)
            return True, "Successfully removed all vector databases"
        else:
            return True, "No vector databases found to remove"
    except Exception as e:
        return False, f"Failed to remove vector databases: {str(e)}"

def collection_exists(collection_name):
    """
    Check if a vector database collection already exists.
    
    Args:
        collection_name (str): Name of the collection to check
        
    Returns:
        bool: True if collection exists, False otherwise
    """
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        chroma_db_path = os.path.join(script_dir, "chroma_db")
        
        if not os.path.exists(chroma_db_path):
            return False
        
        client = chromadb.PersistentClient(path=chroma_db_path)
        
        collections = client.list_collections()
        return any(col.name == collection_name for col in collections)
    except Exception:
        return False

def process_project(input_path, use_temp_dir=True):
    """
    Process either a GitHub repository or local folder for vectorization.
    
    Args:
        input_path (str): GitHub URL or local folder path
        use_temp_dir (bool): For GitHub repos, whether to use temp directory
        
    Returns:
        tuple: (success: bool, message: str, project_path: str, project_name: str, input_type: str, cleanup_needed: bool)
    """
    try:
        # Detect input type
        input_type = detect_input_type(input_path)
        
        if input_type == 'invalid':
            return False, f"Invalid input: '{input_path}' is neither a valid GitHub URL nor an accessible local folder", None, None, None, False
        
        project_name = get_project_name(input_path, input_type)
        
        if input_type == 'github':
            print(f"🔗 Processing GitHub repository: {input_path}")
            success, message, project_path = clone_repository(input_path, use_temp_dir)
            cleanup_needed = use_temp_dir  # Only cleanup if we used temp directory
            
            if not success:
                return False, message, None, project_name, input_type, False
                
        elif input_type == 'local':
            print(f"📁 Processing local folder: {input_path}")
            project_path = os.path.abspath(input_path)
            message = f"Using local folder: {project_path}"
            cleanup_needed = False  # Never cleanup local folders
            
        return True, message, project_path, project_name, input_type, cleanup_needed
        
    except Exception as e:
        return False, f"Error processing project: {str(e)}", None, None, None, False

def cleanup_repository(repo_path):
    """
    Remove a cloned repository directory.
    
    Args:
        repo_path (str): Path to the repository directory
        
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        if os.path.exists(repo_path):
            shutil.rmtree(repo_path)
            return True, f"Successfully removed {repo_path}"
        else:
            return False, f"Directory {repo_path} does not exist"
    except Exception as e:
        return False, f"Failed to remove directory: {str(e)}"

def main():
    """
    Main function to handle command line usage.
    """
    if len(sys.argv) < 2:
        print("Usage: python project_setup.py <command> [options]")
        print("\nCommands:")
        print("  <github_url>           Clone and vectorize a GitHub repository")
        print("  <local_folder_path>    Vectorize a local project folder")
        print("  --list-db              List all vector database collections")
        print("  --cleanup-db           Remove all vector databases")
        print("  --delete-db <name>     Delete a specific collection")
        print("\nOptions for GitHub repository processing:")
        print("  --no-temp              Clone to current directory instead of temp")
        print("\nExamples:")
        print("  python project_setup.py https://github.com/user/repo")
        print("  python project_setup.py C:\\path\\to\\local\\project")
        print("  python project_setup.py --list-db")
        print("  python project_setup.py --cleanup-db")
        print("  python project_setup.py --delete-db my_project")
        sys.exit(1)
    
    command = sys.argv[1]
    
    # Handle database management commands
    if command == "--list-db":
        collections = list_vector_databases()
        if not collections:
            print("📭 No vector databases found.")
        else:
            print(f"📚 Found {len(collections)} vector database collections:")
            print("="*60)
            for name, metadata in collections:
                repo_name = metadata.get('repo_name', 'Unknown')
                created_at = metadata.get('created_at', 'Unknown')
                print(f"🗃️  Collection: {name}")
                print(f"   Repository: {repo_name}")
                print(f"   Created: {created_at}")
                print()
        return
    
    elif command == "--cleanup-db":
        success, message = cleanup_all_vector_databases()
        if success:
            print(f"✅ {message}")
        else:
            print(f"❌ {message}")
        return
    
    elif command == "--delete-db":
        if len(sys.argv) < 3:
            print("❌ Please specify a collection name to delete.")
            print("Usage: python test.py --delete-db <collection_name>")
            sys.exit(1)
        
        collection_name = sys.argv[2]
        success, message = delete_vector_database(collection_name)
        if success:
            print(f"✅ {message}")
        else:
            print(f"❌ {message}")
        return
    
    # Handle project processing (GitHub URL or local folder)
    input_path = command
    use_temp_dir = True
    
    # Check for --no-temp flag (only applies to GitHub repos)
    if len(sys.argv) > 2 and sys.argv[2] == "--no-temp":
        use_temp_dir = False
        print("Using current directory instead of temporary directory (for GitHub repos)")
    
    # Show existing vector databases before processing
    existing_collections = list_vector_databases()
    if existing_collections:
        print(f"📚 Existing vector databases ({len(existing_collections)}):")
        for name, metadata in existing_collections:
            repo_name = metadata.get('repo_name', 'Unknown')
            print(f"   - {name} ({repo_name})")
        print()
    
    print(f"Input: {input_path}")
    
    # Process the project (GitHub repo or local folder)
    success, message, project_path, project_name, input_type, cleanup_needed = process_project(input_path, use_temp_dir)
    
    if success:
        print(f"✅ {message}")
        print(f"Project path: {project_path}")
        print(f"Project type: {input_type}")
        
        # Show some basic info about the project
        if project_path and os.path.exists(project_path):
            file_count = sum(len(files) for _, _, files in os.walk(project_path))
            print(f"Total files: {file_count}")
            
            # Check for common files
            common_files = ['README.md', 'README.txt', 'package.json', 'requirements.txt', 'setup.py', '.gitignore']
            found_files = []
            for file in common_files:
                if os.path.exists(os.path.join(project_path, file)):
                    found_files.append(file)
            
            if found_files:
                print(f"Found common files: {', '.join(found_files)}")
            
            print("\n" + "="*60)
            print("🚀 VECTORIZING PROJECT")
            print("="*60)
            
            # Vectorize the project
            vector_success, vector_message, collection_name = vectorize_repository(project_path, project_name)
            
            if vector_success:
                print(f"\n✅ {vector_message}")
                print(f"\n🎯 Vector database ready for documentation generation!")
                print(f"Collection '{collection_name}' is now available for semantic search.")
                
                # Cleanup cloned repository if needed (only for GitHub repos with temp dir)
                if cleanup_needed and project_path:
                    print(f"\n🧹 Cleaning up temporary directory...")
                    cleanup_success, cleanup_message = cleanup_repository(project_path)
                    if cleanup_success:
                        print(f"✅ {cleanup_message}")
                    else:
                        print(f"⚠️  {cleanup_message}")
            else:
                print(f"\n❌ Vectorization failed: {vector_message}")
                if cleanup_needed and project_path:
                    print("Cleaning up temporary directory...")
                    cleanup_repository(project_path)
    else:
        print(f"❌ {message}")
        sys.exit(1)

if __name__ == "__main__":
    main()