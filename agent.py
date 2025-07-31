from ollama import chat, ChatResponse
from colorama import Fore, Style, init
import chromadb
import os
from typing import List, Dict, Any

# Initialize colorama for colored console output
init(autoreset=True)

def get_chroma_client():
    """Get ChromaDB client with the correct path"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    chroma_db_path = os.path.join(script_dir, "chroma_db")
    return chromadb.PersistentClient(path=chroma_db_path)



def search_repository(query: str, collection_name: str = None, max_results: int = 5) -> str:
    """
    Search the vectorized repository using semantic search.
    
    Args:
        query (str): The search query to find relevant code/documentation
        collection_name (str, optional): Specific collection to search. If None, searches the first available.
        max_results (int): Maximum number of results to return
        
    Returns:
        str: Formatted search results with file paths and relevant code snippets
    """
    try:
        client = get_chroma_client()
        
        # Get available collections
        collections = client.list_collections()
        if not collections:
            return "No vector databases found. Please vectorize a repository first."
        
        # Use specified collection or first available
        if collection_name:
            try:
                collection = client.get_collection(collection_name)
            except:
                return f"Collection '{collection_name}' not found. Available collections: {[c.name for c in collections]}"
        else:
            collection = collections[0]
            collection_name = collection.name
        
        # Perform semantic search
        results = collection.query(
            query_texts=[query],
            n_results=max_results,
            include=["documents", "metadatas", "distances"]
        )
        
        if not results['documents'][0]:
            return f"No relevant results found for query: '{query}'"
        
        # Format results
        formatted_results = []
        formatted_results.append(f"🔍 Search Results for: '{query}'")
        formatted_results.append(f"📚 Collection: {collection_name}")
        formatted_results.append("=" * 60)
        
        for i, (doc, metadata, distance) in enumerate(zip(
            results['documents'][0], 
            results['metadatas'][0], 
            results['distances'][0]
        )):
            file_path = metadata.get('file_path', 'Unknown')
            file_type = metadata.get('file_type', '')
            chunk_index = metadata.get('chunk_index', 0)
            
            formatted_results.append(f"\n📄 Result {i+1} (Relevance: {1-distance:.3f})")
            formatted_results.append(f"📁 File: {file_path}")
            formatted_results.append(f"🧩 Chunk: {chunk_index}")
            if file_type:
                formatted_results.append(f"📝 Type: {file_type}")
            formatted_results.append("─" * 40)
            formatted_results.append(doc[:500] + ("..." if len(doc) > 500 else ""))
            formatted_results.append("")
        
        return "\n".join(formatted_results)
        
    except Exception as e:
        return f"Error searching repository: {str(e)}"

def list_repository_collections() -> str:
    """
    List all available vectorized repository collections.
    
    Returns:
        str: Formatted list of available collections with metadata
    """
    try:
        client = get_chroma_client()
        collections = client.list_collections()
        
        if not collections:
            return "📭 No vector databases found. Please vectorize a repository first."
        
        formatted_results = []
        formatted_results.append(f"📚 Available Repository Collections ({len(collections)}):")
        formatted_results.append("=" * 60)
        
        for collection in collections:
            metadata = collection.metadata or {}
            repo_name = metadata.get('repo_name', 'Unknown')
            created_at = metadata.get('created_at', 'Unknown')
            
            # Get collection stats
            try:
                count = collection.count()
            except:
                count = "Unknown"
            
            formatted_results.append(f"\n🗃️  Collection: {collection.name}")
            formatted_results.append(f"📦 Repository: {repo_name}")
            formatted_results.append(f"📊 Document chunks: {count}")
            formatted_results.append(f"📅 Created: {created_at}")
            formatted_results.append("")
        
        return "\n".join(formatted_results)
        
    except Exception as e:
        return f"Error listing collections: {str(e)}"

def analyze_repository_structure(collection_name: str = None) -> str:
    """
    Analyze the structure and content of a vectorized repository.
    
    Args:
        collection_name (str, optional): Specific collection to analyze. If None, analyzes the first available.
        
    Returns:
        str: Detailed analysis of repository structure, file types, and content overview
    """
    try:
        client = get_chroma_client()
        collections = client.list_collections()
        
        if not collections:
            return "No vector databases found. Please vectorize a repository first."
        
        # Use specified collection or first available
        if collection_name:
            try:
                collection = client.get_collection(collection_name)
            except:
                return f"Collection '{collection_name}' not found."
        else:
            collection = collections[0]
            collection_name = collection.name
        
        # Get all documents and metadata
        all_data = collection.get(include=["metadatas"])
        metadatas = all_data['metadatas']
        
        if not metadatas:
            return f"No data found in collection '{collection_name}'"
        
        # Analyze file types and structure
        file_types = {}
        files = set()
        total_chunks = len(metadatas)
        
        for metadata in metadatas:
            file_path = metadata.get('file_path', 'Unknown')
            file_type = metadata.get('file_type', 'Unknown')
            
            files.add(file_path)
            file_types[file_type] = file_types.get(file_type, 0) + 1
        
        # Format analysis results
        formatted_results = []
        formatted_results.append(f"📊 Repository Structure Analysis")
        formatted_results.append(f"📚 Collection: {collection_name}")
        formatted_results.append("=" * 60)
        
        formatted_results.append(f"\n📈 Overview:")
        formatted_results.append(f"  📁 Total files: {len(files)}")
        formatted_results.append(f"  🧩 Total chunks: {total_chunks}")
        formatted_results.append(f"  📊 Avg chunks per file: {total_chunks/len(files):.1f}")
        
        formatted_results.append(f"\n📝 File Types:")
        for file_type, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_chunks) * 100
            formatted_results.append(f"  {file_type or 'No extension'}: {count} chunks ({percentage:.1f}%)")
        
        formatted_results.append(f"\n📂 Sample Files:")
        sample_files = sorted(list(files))[:10]
        for file_path in sample_files:
            formatted_results.append(f"  📄 {file_path}")
        
        if len(files) > 10:
            formatted_results.append(f"  ... and {len(files) - 10} more files")
        
        return "\n".join(formatted_results)
        
    except Exception as e:
        return f"Error analyzing repository: {str(e)}"

def get_file_content(file_path: str, collection_name: str = None) -> str:
    """
    Retrieve the complete content of a specific file from the vectorized repository.
    
    Args:
        file_path (str): The relative path to the file within the repository
        collection_name (str, optional): Specific collection to search. If None, searches the first available.
        
    Returns:
        str: Complete file content reconstructed from chunks, or error message
    """
    try:
        client = get_chroma_client()
        collections = client.list_collections()
        
        if not collections:
            return "No vector databases found. Please vectorize a repository first."
        
        # Use specified collection or first available
        if collection_name:
            try:
                collection = client.get_collection(collection_name)
            except:
                return f"Collection '{collection_name}' not found. Available collections: {[c.name for c in collections]}"
        else:
            collection = collections[0]
            collection_name = collection.name
        
        # Get all chunks for the specific file
        all_data = collection.get(
            include=["documents", "metadatas"],
            where={"file_path": file_path}
        )
        
        if not all_data['documents']:
            return f"File '{file_path}' not found in collection '{collection_name}'"
        
        # Sort chunks by chunk_index to reconstruct the file
        chunks_with_metadata = list(zip(all_data['documents'], all_data['metadatas']))
        chunks_with_metadata.sort(key=lambda x: x[1].get('chunk_index', 0))
        
        # Reconstruct the file content
        file_content = "".join([chunk[0] for chunk in chunks_with_metadata])
        
        # Get file metadata
        first_metadata = chunks_with_metadata[0][1]
        file_type = first_metadata.get('file_type', '')
        file_size = first_metadata.get('file_size', 'Unknown')
        
        # Format the response
        formatted_result = []
        formatted_result.append(f"📄 File Content: {file_path}")
        formatted_result.append(f"📚 Collection: {collection_name}")
        if file_type:
            formatted_result.append(f"📝 Type: {file_type}")
        formatted_result.append(f"📊 Size: {file_size} bytes")
        formatted_result.append(f"🧩 Chunks: {len(chunks_with_metadata)}")
        formatted_result.append("=" * 60)
        formatted_result.append(file_content)
        
        return "\n".join(formatted_result)
        
    except Exception as e:
        return f"Error retrieving file content: {str(e)}"


def main():
    system_msg = (
        "You are an AI documentation agent with access to vectorized repository data. You have access to these tools:\n"
        "1. search_repository(query, collection_name=None, max_results=5): Search for relevant code/documentation using semantic search\n"
        "2. list_repository_collections(): List all available vectorized repository collections\n"
        "3. analyze_repository_structure(collection_name=None): Analyze repository structure and file types\n"
        "4. get_file_content(file_path, collection_name=None): Retrieve complete content of a specific file from the repository\n\n"
        "Use these tools to help users understand codebases, generate documentation, and answer questions about repositories.\n"
        "Always search for relevant information before providing answers about code or documentation."
    )

    messages = [{"role": "system", "content": system_msg}]
    tools = [search_repository, list_repository_collections, analyze_repository_structure, get_file_content]

    print(Fore.GREEN + "Simple agent ready! Type 'exit' to quit." + Style.RESET_ALL)

    while True:
        user_input = input(Fore.CYAN + "User: " + Style.RESET_ALL)
        if not user_input or user_input.lower() in ("exit", "quit"):
            print(Fore.YELLOW + "Goodbye!" + Style.RESET_ALL)
            break

        # Add user message
        messages.append({"role": "user", "content": user_input})
        
        # Get response from Ollama
        response: ChatResponse = chat(
            model="qwen3",
            messages=messages,
            tools=tools,
            stream=False
        )

        # Execute any tool calls
        for call in response.message.tool_calls or []:
            fn_name = call.function.name
            args = call.function.arguments or {}
            
            # Execute the tool
            if fn_name in [tool.__name__ for tool in tools]:
                result = globals()[fn_name](**args)
                print(Fore.YELLOW + f"[Tool] {result}" + Style.RESET_ALL)
                messages.append({
                    "role": "tool",
                    "name": fn_name,
                    "content": result
                })

        # Get final response
        final: ChatResponse = chat(
            model="qwen3",
            messages=messages
        )
        print(Fore.MAGENTA + final.message.content + Style.RESET_ALL)
        messages.append({"role": "assistant", "content": final.message.content})


if __name__ == "__main__":
    main()
