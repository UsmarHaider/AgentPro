from .base_tool import Tool
import json
from typing import Any, Optional, Dict
from pydantic import PrivateAttr
import requests
import os

class TraversaalProRAGTool(Tool):
    name: str = "Traversaal Pro RAG"
    action_type: str = "traversaalpro_rag"
    input_format: str = "A query string for document search. Example: 'chemical safety protocol'"
    description: str = "Searches documents using the Traversaal Pro RAG API and returns a context-aware answer and document excerpts."

    _api_key: str = PrivateAttr(default="")

    def __init__(self, api_key: Optional[str] = None, document_info: Optional[str] = None, **data):
        if document_info:
            data["description"] = (
                f"Searches {document_info} documents using the Traversaal Pro RAG API and returns a context-aware answer and document excerpts."
            )

        super().__init__(**data)
        
        # Store the API key as a private attribute
        self._api_key = api_key or os.getenv("TRAVERSAAL_PRO_API_KEY", "")
        
        # Validate API key
        if not self._api_key:
            raise ValueError("API key is required. Provide it directly or set TRAVERSAAL_PRO_API_KEY environment variable.")

    def run(self, input: Any) -> str:
        if not isinstance(input, str):
            return "❌ Error: Expected a query string. Example: 'chemical safety protocol'"

        url = "https://pro-documents.traversaal-api.com/documents/search"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "query": input.strip("'\""),
            "rag": True
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()  # This will raise an exception for HTTP error codes

            result = response.json()
            
            # Use the correct keys from the response
            answer = result.get("response", "").strip()
            references = result.get("references", [])

            if not answer:
                return "No answer found for this query. Please try a different question."

            output = f"**Answer:**\n{answer}\n\n"

            if references:
                output += "**Source Document Snippets:**\n"
                for idx, ref in enumerate(references, 1):
                    file_id = ref.get("file_id", "Unknown")
                    s3_key = ref.get("s3_bucket_key", "")
                    file_name = s3_key.split("/")[-1] if s3_key else "Unknown Document"
                    snippet = ref.get("chunk_text", "").strip()
                    score = ref.get("score", 0)
                    
                    output += f"{idx}. *{file_name}* (Relevance: {score:.2f})\n{snippet[:500]}...\n\n"

            return output.strip()

        except requests.exceptions.HTTPError as e:
            return f"❌ API Error: {e.response.status_code} - {e.response.text}"
        except requests.exceptions.RequestException as e:
            return f"❌ HTTP Request Error: {e}"
        except Exception as e:
            return f"❌ Unexpected Error: {e}"
