# Import required libraries
import os  # For environment variables
from typing import TypedDict, List, Dict, Any  # Type hints for better code documentation
from langgraph.graph import StateGraph, END  # LangGraph for workflow management
from langchain_openai import ChatOpenAI  # OpenAI LLM integration
from langchain.schema import HumanMessage, SystemMessage  # Message types for LLM communication
import json  # JSON handling for data structures
import re  # Regular expressions (imported but not used)
import requests  # HTTP requests for web search functionality
from dotenv import load_dotenv  # Load environment variables from .env file

# Load environment variables from .env file
load_dotenv()

# Define the state structure for the LangGraph workflow
class ISOStandardState(TypedDict):
    query: str  # User's input query
    standard_info: Dict[str, Any]  # Processed information about ISO standards
    web_search_results: str  # Results from web search
    response: str  # Final formatted response to user
    conversation_history: List[Dict[str, str]]  # Chat history for context

# Main agent class for ISO medical device standards
class ISOMedicalStandardAgent:
    def __init__(self, openai_api_key: str):
        # Initialize main LLM for general processing
        self.llm = ChatOpenAI(
            api_key=openai_api_key,  # OpenAI API key
            model="gpt-4.1-mini",  # GPT model version
            temperature=0.1  # Low temperature for consistent responses
        )
        # Initialize separate LLM for web search query generation
        self.search_llm = ChatOpenAI(
            api_key=openai_api_key,  # Same API key
            model="gpt-4.1-mini",  # Same model
            temperature=0.1  # Low temperature for focused search queries
        )
        # Build and compile the workflow graph
        self.graph = self._build_graph()
        
    def keyword_search(self, keywords: str) -> Dict[str, Any]:
        """Search ISO standards database using keywords"""
        iso_standards_db = {
            "ISO 13485": {
                "topic": "Quality Management Systems for Medical Devices",
                "scope": "Requirements for quality management system for medical device organizations",
                "product_application": "All medical devices and related services",
                "publication_date": "2016 (current version)",
                "description": "Specifies requirements for a quality management system where an organization needs to demonstrate its ability to provide medical devices and related services that consistently meet customer and applicable regulatory requirements."
            },
            "ISO 14971": {
                "topic": "Risk Management for Medical Devices",
                "scope": "Application of risk management to medical devices",
                "product_application": "All medical devices throughout their lifecycle",
                "publication_date": "2019 (current version)",
                "description": "Specifies a process for a manufacturer to identify the hazards associated with medical devices, to estimate and evaluate the associated risks, to control these risks, and to monitor the effectiveness of the controls."
            },
            "IEC 62304": {
                "topic": "Medical Device Software - Software Life Cycle Processes",
                "scope": "Software development life cycle processes for medical device software",
                "product_application": "Medical device software and software as medical devices",
                "publication_date": "2006 (current version)",
                "description": "Defines the life cycle requirements for medical device software. The processes, activities, and tasks described in this standard establish a common framework for medical device software life cycle processes."
            }
        }
        
        keywords_lower = keywords.lower()
        results = {}
        
        for standard_id, info in iso_standards_db.items():
            # Search in all text fields
            searchable_text = f"{info['topic']} {info['scope']} {info['product_application']} {info['description']}".lower()
            if keywords_lower in searchable_text:
                results[standard_id] = info
                
        return results
        
    def _build_graph(self):
        # Create a new StateGraph with our defined state structure
        workflow = StateGraph(ISOStandardState)
        
        # Add nodes (processing steps) to the workflow
        workflow.add_node("analyze_query", self._analyze_query)  # Step 1: Analyze user query
        workflow.add_node("web_search", self._web_search)  # Step 2: Perform web search
        workflow.add_node("extract_standard_info", self._extract_standard_info)  # Step 3: Extract ISO info
        workflow.add_node("format_response", self._format_response)  # Step 4: Format final response
        
        # Define the workflow sequence
        workflow.set_entry_point("analyze_query")  # Start with query analysis
        workflow.add_edge("analyze_query", "web_search")  # Then web search
        workflow.add_edge("web_search", "extract_standard_info")  # Then extract info
        workflow.add_edge("extract_standard_info", "format_response")  # Then format response
        workflow.add_edge("format_response", END)  # End the workflow
        
        # Compile and return the executable workflow
        return workflow.compile()
    
    def _analyze_query(self, state: ISOStandardState) -> ISOStandardState:
        # Extract the user query from state
        query = state["query"]
        
        # Define system prompt for query analysis
        system_prompt = """You are an expert in ISO medical device standards. 
        Analyze the user query and determine if it's asking about:
        1. A specific ISO standard number
        2. A medical device category
        3. A general inquiry about medical standards
        
        Extract any ISO standard numbers mentioned (e.g., ISO 13485, ISO 14971, etc.)."""
        
        # Create message list for LLM
        messages = [
            SystemMessage(content=system_prompt),  # System instructions
            HumanMessage(content=f"Query: {query}")  # User query
        ]
        
        # Get analysis from LLM
        response = self.llm.invoke(messages)
        # Store analysis results in state
        state["standard_info"] = {"analysis": response.content}
        return state
    
    def _web_search(self, state: ISOStandardState) -> ISOStandardState:
        # Get user query from state
        query = state["query"]
        
        # Create search query for ISO standards using LLM
        search_prompt = f"""Create a web search query to find current information about ISO medical device standards based on this user query: {query}
        
        Focus on finding:
        - Official ISO standard documents
        - Publication dates and current versions
        - Scope and application information
        - Medical device regulatory information
        
        Return only the search query, nothing else."""
        
        # Prepare messages for search LLM
        messages = [
            SystemMessage(content=search_prompt),  # Instructions for search query creation
            HumanMessage(content=query)  # Original user query
        ]
        
        # Generate search query using dedicated search LLM
        search_query_response = self.search_llm.invoke(messages)
        search_query = search_query_response.content.strip()  # Clean the response
        
        # Simulate web search results (in real implementation, you would use actual search API)
        search_results = f"""Search query: {search_query}
        
        Recent ISO medical device standards information:
        - ISO standards are regularly updated and maintained by the International Organization for Standardization
        - Medical device standards focus on quality management, risk management, and software lifecycle processes
        - Current versions should be verified through official ISO website or regulatory bodies
        - Standards may have amendments or technical corrigenda that update requirements
        
        Note: For most current information, consult official ISO catalog or regulatory guidance documents."""
        
        # Store search results in state
        state["web_search_results"] = search_results
        return state
    
    def _extract_standard_info(self, state: ISOStandardState) -> ISOStandardState:
        # Get user query and web search results from state
        query = state["query"]
        web_results = state.get("web_search_results", "")  # Get web results or empty string
        
        # Built-in database of medical device ISO standards
        iso_standards_db = {
            # ISO 13485: Quality Management Systems
            "ISO 13485": {
                "topic": "Quality Management Systems for Medical Devices",
                "scope": "Requirements for quality management system for medical device organizations",
                "product_application": "All medical devices and related services",
                "publication_date": "2016 (current version)",
                "description": "Specifies requirements for a quality management system where an organization needs to demonstrate its ability to provide medical devices and related services that consistently meet customer and applicable regulatory requirements."
            },
            # ISO 14971: Risk Management
            "ISO 14971": {
                "topic": "Risk Management for Medical Devices",
                "scope": "Application of risk management to medical devices",
                "product_application": "All medical devices throughout their lifecycle",
                "publication_date": "2019 (current version)",
                "description": "Specifies a process for a manufacturer to identify the hazards associated with medical devices, to estimate and evaluate the associated risks, to control these risks, and to monitor the effectiveness of the controls."
            },
            # IEC 62304: Software Life Cycle
            "IEC 62304": {
                "topic": "Medical Device Software - Software Life Cycle Processes",
                "scope": "Software development life cycle processes for medical device software",
                "product_application": "Medical device software and software as medical devices",
                "publication_date": "2006 (current version)",
                "description": "Defines the life cycle requirements for medical device software. The processes, activities, and tasks described in this standard establish a common framework for medical device software life cycle processes."
            }
        }
        
        # Create comprehensive system prompt combining database and web search results
        system_prompt = f"""You are an ISO medical device standards expert. Based on the user query and web search results, provide detailed information about relevant ISO standards.

Available standards database: {json.dumps(iso_standards_db, indent=2)}

Web search results: {web_results}

For each relevant standard, provide:
1. Topic: What the standard covers
2. Scope: The range and boundaries of the standard
3. Product Application: Which medical devices/products it applies to
4. Publication Date: When it was published/last updated

Combine information from the database and web search results. If web search indicates newer versions or updates, mention them.
If the query mentions a specific ISO number, focus on that. If it's about a device category, suggest relevant standards.
If the standard is not in the database, use web search results and your knowledge to provide information."""
        
        # Prepare messages for LLM processing
        messages = [
            SystemMessage(content=system_prompt),  # Expert instructions with data
            HumanMessage(content=f"User query: {query}")  # User's original query
        ]
        
        # Extract and process standard information using LLM
        response = self.llm.invoke(messages)
        # Store extracted information in state
        state["standard_info"]["extracted_info"] = response.content
        return state
    
    def _format_response(self, state: ISOStandardState) -> ISOStandardState:
        # Get the extracted information from previous step
        extracted_info = state["standard_info"]["extracted_info"]
        
        # Define formatting instructions for consistent output
        system_prompt = """Format the ISO standard information in a clear, structured way for the user.
        Use the following format:

        📋 **ISO Standard Information**
        
        **Standard:** [ISO Number and Title]
        **Topic:** [Main subject area]
        **Scope:** [What it covers]
        **Product Application:** [Which devices/products]
        **Publication Date:** [When published/updated]
        
        **Summary:** [Brief description]
        
        If multiple standards are relevant, list them separately.
        Be concise but comprehensive."""
        
        # Prepare messages for final formatting
        messages = [
            SystemMessage(content=system_prompt),  # Formatting instructions
            HumanMessage(content=f"Information to format: {extracted_info}")  # Raw info to format
        ]
        
        # Format the final response using LLM
        response = self.llm.invoke(messages)
        # Store final formatted response in state
        state["response"] = response.content
        return state
    
    def chat(self, query: str, conversation_history: List[Dict[str, str]] = None) -> str:
        # Initialize conversation history if not provided
        if conversation_history is None:
            conversation_history = []
            
        # Create initial state for the workflow
        initial_state = {
            "query": query,  # User's input query
            "standard_info": {},  # Empty dict to store standard information
            "web_search_results": "",  # Empty string for search results
            "response": "",  # Empty string for final response
            "conversation_history": conversation_history  # Chat history for context
        }
        
        # Execute the complete workflow and get final result
        result = self.graph.invoke(initial_state)
        # Return the formatted response to user
        return result["response"]

# Main function to run the command-line interface
def main():
    # Load environment variables from .env file
    load_dotenv()
    
    # Load OpenAI API key from environment variables
    api_key = os.getenv("OPENAI_API_KEY")
    # Check if API key is available
    if not api_key:
        print("Please set your OPENAI_API_KEY environment variable")
        return
    
    # Initialize the ISO medical standards agent
    agent = ISOMedicalStandardAgent(api_key)
    
    # Display welcome message and instructions
    print("🏥 ISO Medical Device Standards Chatbot")
    print("Ask me about ISO standards for medical devices!")
    print("Type 'quit' to exit\n")
    
    # Initialize conversation history list
    conversation_history = []
    
    # Main chat loop
    while True:
        # Get user input
        user_input = input("You: ").strip()
        
        # Check for exit commands
        if user_input.lower() in ['quit', 'exit', 'bye']:
            print("Goodbye!")
            break
            
        # Skip empty inputs
        if not user_input:
            continue
            
        try:
            # Process user query through the agent
            response = agent.chat(user_input, conversation_history)
            # Display bot response with custom name
            print(f"\nZenTH med_bot: {response}\n")
            
            # Update conversation history for context
            conversation_history.append({"user": user_input, "bot": response})
            
            # Keep only last 5 exchanges to manage memory
            if len(conversation_history) > 5:
                conversation_history = conversation_history[-5:]
                
        except Exception as e:
            # Handle any errors during processing
            print(f"Error: {e}")

# Run the main function if script is executed directly
if __name__ == "__main__":
    main()