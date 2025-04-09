# servo_rag.py
from langchain.docstore.document import Document 
from langchain_community.vectorstores import FAISS
from langchain_ollama import ChatOllama
from langchain_ollama import OllamaEmbeddings
from typing import Annotated, Sequence, Literal
from typing_extensions import TypedDict 
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langgraph.graph.message import add_messages 
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field
from langgraph.prebuilt import tools_condition 
from langgraph.graph import END, StateGraph, START 
from langgraph.prebuilt import ToolNode 
from langchain.tools.retriever import create_retriever_tool
import sys 

from fermia_servo import ServoController

def get_servo_controller():
    try:
        controller = ServoController(
            channels=16,
            redis_host='localhost',
            redis_port=6379,
            redis_db=0,
            redis_key_prefix='servo:'
        )
        return controller, None
    except Exception as e:
        return None, str(e)

class Grade(BaseModel):
    """Binary score for relevance check."""
    binary_score: str = Field(description="Relevance score 'yes' or 'no'")

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

def setup_rag_system():
    # Initialize controller 
    controller, error = get_servo_controller() 
    if error:
        print(f"Warning: Servo controller initialization error: {error}")
    else:
        motor_dict = controller.get_all_servos()

    # Create documents from motor data
    documents = []
    for key, info in motor_dict.items():
        content = (
            f"Motor name: {info['name']}. Channel: {info['channel']}. "
            f"Angle: {info['angle']} (default: {info['default_angle']}). "
            f"Speed: {info['speed']} (default: {info['default_speed']})."
        )
        documents.append(Document(page_content=content, metadata={"id": key}))

    # Add to vectorDB 
    vectorstore = FAISS.from_documents(
        documents=documents,
        embedding=OllamaEmbeddings(model="nomic-embed-text"), 
    )

    retriever = vectorstore.as_retriever()

    retriever_tool = create_retriever_tool(
        retriever,
        "retrieve_motor_data",
        "Retrieve detailed motor data including channel, angle, and speed information."
    )

    tools = [retriever_tool]
    
    def grade_documents(state) -> Literal["generate", "rewrite"]:
        """Determines whether the retrieved documents are relevant to the question."""
        # Data model for grading
        model = ChatOllama(temperature=0, model="qwen2.5:7b", streaming=True)
        llm_with_tool = model.with_structured_output(Grade)
        
        # Prompt for relevance check
        prompt = PromptTemplate(
            template="""You are a grader assessing relevance of a retrieved document to a user question.
            Here is the retrieved document: \n\n {context} \n\n
            Here is the user question: {question} \n
            If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant.
            Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question.""",
            input_variables=["context", "question"],
        )
        
        # Create and run the chain
        chain = prompt | llm_with_tool
        messages = state["messages"]
        question = messages[0].content
        docs = messages[-1].content
        
        # Get and evaluate the result
        scored_result = chain.invoke({"question": question, "context": docs})
        score = scored_result.binary_score
        
        if score == "yes":
            return "generate"
        else:
            return "rewrite"

    def agent(state):
        """Agent to decide what action to take."""
        messages = state["messages"]
        model = ChatOllama(temperature=0, model="qwen2.5:7b", streaming=True)
        model = model.bind_tools(tools)
        response = model.invoke(messages)
        return {"messages": [response]}

    def rewrite(state):
        """Rewrite the query if original didn't get relevant results."""
        messages = state["messages"]
        question = messages[0].content
        
        msg = [
            HumanMessage(
                content=f"""Look at the input and try to reason about the underlying semantic intent.
                Here is the initial question: {question}
                Formulate an improved question:"""
            )
        ]
        
        model = ChatOllama(temperature=0, model="qwen2.5:7b", streaming=True)
        response = model.invoke(msg)
        return {"messages": [HumanMessage(content=response.content)]}

    def generate(state):
        """Generate the final answer."""
        messages = state["messages"]
        question = messages[0].content
        docs = messages[-1].content
        
        # Create a simple RAG prompt template
        prompt_template = """
        You are an assistant for question-answering about motor data. 
        Use the following retrieved information to answer the question.
        If you don't know the answer, just say that you don't know.
        
        Question: {question}
        
        Context: {context}
        
        Answer:
        """
        prompt = PromptTemplate.from_template(prompt_template)
        
        # Setup the LLM and chain
        llm = ChatOllama(model="qwen2.5:7b", temperature=0, streaming=True)
        rag_chain = prompt | llm | StrOutputParser()
        
        # Run the chain and return the response
        response = rag_chain.invoke({"context": docs, "question": question})
        return {"messages": [AIMessage(content=response)]}

    # Define the graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("agent", agent)
    retrieve = ToolNode([retriever_tool])
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("rewrite", rewrite)
    workflow.add_node("generate", generate)

    # Add edges
    workflow.add_edge(START, "agent")

    # Decide whether to retrieve
    workflow.add_conditional_edges(
        "agent",
        tools_condition,
        {
            "tools": "retrieve",
            END: END,
        },
    )

    # Check document relevance
    workflow.add_conditional_edges(
        "retrieve",
        grade_documents,
        {
            "generate": "generate",
            "rewrite": "rewrite"
        }
    )

    workflow.add_edge("generate", END)
    workflow.add_edge("rewrite", "agent")

    # Compile the graph
    return workflow.compile()

def query_servo_rag(query_text):
    """
    Run a query through the servo RAG system and return the answer.
    
    Args:
        query_text (str): The query text to process
        
    Returns:
        str: The response from the RAG system
    """
    # Setup the RAG system
    graph = setup_rag_system()
    
    # Prepare the input
    inputs = {
        "messages": [
            HumanMessage(content=query_text)
        ]
    }
    
    # Process each step in the stream and collect the final result
    final_result = None
    for output in graph.stream(inputs):
        # Keep updating with latest result
        for key, value in output.items():
            final_result = value
    
    # Extract and return final answer
    if final_result and "messages" in final_result:
        final_messages = final_result["messages"]
        if final_messages:
            return final_messages[-1].content
    return "Unable to process query"

def main():

    if len(sys.argv) != 2:
        sys.exit(1)

    prompt = sys.argv[1]
    response = query_servo_rag(prompt)
    print(response)
    
if __name__ == "__main__":
    main()