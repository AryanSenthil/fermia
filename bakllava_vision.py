import sys
from langchain_ollama import OllamaLLM
import time 
import fermia_camera

def camera_vision(prompt: str) -> str:
    """
    Capture an image from the stream and process it with Bakllava LLM.
    
    Args:
        prompt (str): A question or prompt related to the image.
        
    Returns:
        str: The response from the LLM or an error message.
    """
    
    try:
        # Capture frame from stream and get base64 string
        for _ in range(5):
            base64_image = fermia_camera.get_base64_image()
            time.sleep(0.05)

        if base64_image is None:
            return "Failed to capture image from stream."
            
        # Initialize the LLM for image processing 
        llm = OllamaLLM(model="bakllava", temperature=0.0)
        llm_with_image_context = llm.bind(images=[base64_image])
        
        # Process image with LLM
        response = llm_with_image_context.invoke(prompt)
        return response
        
    except Exception as e:
        error_msg = f"Error processing image with LLM: {e}"
        return error_msg
