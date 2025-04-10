import streamlit as st
import os
import subprocess
import signal
import psutil
import time
import uuid
import datetime
from typing import Dict, Any, List, Tuple
from graph import invoke_our_graph

def initialize_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "processing" not in st.session_state:
        st.session_state.processing = False
    if "conversation_history" not in st.session_state:
        # Initialize the conversation history for LangGraph
        st.session_state.conversation_history = []
    if "thread_id" not in st.session_state:
        # Create a unique thread ID for this conversation
        st.session_state.thread_id = str(uuid.uuid4())
    if "all_conversations" not in st.session_state:
        # Dictionary to store all conversations: {thread_id: (title, timestamp, messages)}
        st.session_state.all_conversations = {}
    if "current_thread_id" not in st.session_state:
        st.session_state.current_thread_id = st.session_state.thread_id

def save_current_conversation():
    """Save the current conversation to the all_conversations dictionary."""
    if st.session_state.messages:
        # Only save if there are messages
        thread_id = st.session_state.current_thread_id
        
        # Create a title from the first user message or use default
        title = "New Conversation"
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                # Use first 30 chars of first user message as title
                title = msg["content"][:30] + ("..." if len(msg["content"]) > 30 else "")
                break
                
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Save the conversation
        st.session_state.all_conversations[thread_id] = (
            title, 
            timestamp,
            st.session_state.messages.copy(),
            st.session_state.conversation_history.copy()
        )

def create_new_conversation():
    """Create a new conversation by saving current one and resetting."""
    # Save current conversation first if it has content
    save_current_conversation()
    
    # Create a new thread ID
    new_thread_id = str(uuid.uuid4())
    st.session_state.thread_id = new_thread_id
    st.session_state.current_thread_id = new_thread_id
    
    # Reset current conversation
    st.session_state.messages = []
    st.session_state.conversation_history = []
    
    st.rerun()
    
def load_conversation(thread_id: str):
    """Load a conversation by its thread ID."""
    # Save current conversation first
    save_current_conversation()
    
    # Load the selected conversation
    if thread_id in st.session_state.all_conversations:
        _, _, messages, conversation_history = st.session_state.all_conversations[thread_id]
        st.session_state.messages = messages.copy()
        st.session_state.conversation_history = conversation_history.copy()
        st.session_state.thread_id = thread_id
        st.session_state.current_thread_id = thread_id
        st.rerun()

def display_chat_history():
    """Display all messages in the chat history."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

def process_langgraph_response(response: Dict[str, Any]) -> str:
    """Extract the final content from LangGraph response."""
    try:
        # Get all messages from the response
        messages = response["messages"]
        # Find the last substantive message from the assistant
        for message in reversed(messages):
            # Skip transfer messages and intermediate steps
            if (hasattr(message, 'content') and
                not any(skip in message.content.lower()
                        for skip in ['transfer', 'successfully transferred'])):
                return message.content
        # If no suitable message found
        return "Sorry, I couldn't process that request."
    except Exception as e:
        st.error(f"Error processing response: {str(e)}")
        return "Sorry, I couldn't process that request."

def update_conversation_history(role: str, content: str):
    """Update the conversation history with a new message."""
    # Add message to the conversation history
    st.session_state.conversation_history.append({"role": role, "content": content})

def main():
    # Initialize session state
    initialize_session_state()
    
    # Sidebar with conversation history and options
    with st.sidebar:
        st.title("Chat History")
        
        # New conversation button
        if st.button("New Conversation", key="new_convo_btn"):
            create_new_conversation()
        
        st.divider()
        
        # Display all saved conversations as clickable items
        if st.session_state.all_conversations:
            st.subheader("Previous Conversations")
            
            # Save current conversation before displaying so it appears in the list
            save_current_conversation()
            
            # Sort conversations by timestamp (newest first)
            sorted_convos = sorted(
                st.session_state.all_conversations.items(),
                key=lambda x: x[1][1],  # Sort by timestamp
                reverse=True  # Newest first
            )
            
            for thread_id, (title, timestamp, _, _) in sorted_convos:
                # Create a unique key for each button
                button_key = f"convo_{thread_id}"
                
                # Highlight current conversation
                if thread_id == st.session_state.current_thread_id:
                    button_label = f"➤ {title}\n{timestamp}"
                else:
                    button_label = f"{title}\n{timestamp}"
                
                if st.button(button_label, key=button_key):
                    load_conversation(thread_id)
    
    # Display current chat messages
    display_chat_history()
    
    # Handle user input
    if prompt := st.chat_input("How can I help you?"):
        if not st.session_state.processing:
            st.session_state.processing = True
            # Display user message
            st.chat_message("user").markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            # Update conversation history
            update_conversation_history("user", prompt)
            
            try:
                # Get response from LangGraph using the thread ID for persistence
                with st.spinner("Thinking..."):
                    response = invoke_our_graph(
                        messages=st.session_state.conversation_history,
                        thread_id=st.session_state.thread_id
                    )
                
                # Process the response
                assistant_response = process_langgraph_response(response)
                
                # Display assistant response
                with st.chat_message("assistant"):
                    st.markdown(assistant_response)
                
                # Add assistant response to display history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": assistant_response
                })
                
                # Update conversation history with assistant's response
                update_conversation_history("assistant", assistant_response)
                
                # Save the updated conversation
                save_current_conversation()
                
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
            finally:
                st.session_state.processing = False
                st.rerun()

if __name__ == "__main__":
    main()