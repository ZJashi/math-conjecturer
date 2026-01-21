import os

from dotenv import find_dotenv, load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.config import get_stream_writer

from schema import AgentBrainstormResult, Proposal, ScrutinyResult
from src.parser.parser import (
    escape_slashes,
    parse_xml_into_proposals,
    render_xml_in_markdown,
    sanitize_memory,
)
from workflow import GraphState

# --- Load Environment Variables ---
dotenv_path = find_dotenv()
load_dotenv(dotenv_path)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


# --- Model Initialization ---
model_name = "google/gemini-2.5-flash-lite"
print(f"--- Initializing Language Model: {model_name} ---")

model = ChatOpenAI(
    model=model_name,
    openai_api_key=OPENROUTER_API_KEY,
    openai_api_base="https://openrouter.ai/api/v1",
    default_headers=None,
)
print(f"  > Model {model_name} initialized.")


# --- Specialist Agent (SA) Node Factory ---

def create_specialist_node(specialty: str, agent_name: str):
    """Factory to create a specialist agent node."""

    prompt = ChatPromptTemplate.from_messages([
        ("system", BASE_SYSTEM_PROMPT),
        ("human", BRAINSTORM_PROMPT)
    ])

    chain = prompt | model.with_structured_output(AgentBrainstormResult)

    def specialist_node(state: GraphState) -> dict:
        writer = get_stream_writer()  # Chainlit streaming
        writer({
                   "msg": f"--- 🤔💭 {agent_name} is brainstroming for proposals ... (Round {state['round_number']}/{state['max_rounds']}) ---"})
        print(f"--- Calling {agent_name} ---")

        response = chain.invoke({
            "round_number": state['round_number'],
            "max_rounds": state['max_rounds'],
            "specialty": specialty,
            "agent_name": agent_name,
            "snippet": sanitize_memory(state['blackboard']),
            "agenda": sanitize_memory(state['blackboard']),
            "blackboard": sanitize_memory(state['blackboard'])
            #"direction": state['human_input_direction'],
        })

        proposals_xml = response.xml_list[0].xml
        proposals_xml = proposals_xml.replace(r'```xml', '').replace(r'```', '')
        proposals_xml = escape_slashes(proposals_xml)
        print("RAW Proposals XML:")
        print(proposals_xml)

        # # Parse XML into proposals list for state update
        proposals_list = parse_xml_into_proposals(proposals_xml)

        # Convert XML to markdown for Chainlit display
        proposals_markdown = render_xml_in_markdown(proposals_xml, "Proposals Overview")

        msg = f"--- 💡 New proposals from {agent_name} in Round {state['round_number']}/{state['max_rounds']} ---\n"
        msg += "New Proposals:\n"
        msg += proposals_markdown
        writer({"msg": msg})

        return {"new_proposals": proposals_list, "new_proposals_xml": [proposals_xml]}

    return specialist_node


# --- Coordinator Agent (CA) Nodes ---

def set_agenda_node(state: GraphState) -> dict:
    """CA Node: Sets the agenda for the round."""
    new_round_number = state['round_number'] + 1  # new round
    print(f"--- Calling CA: Set Agenda (Round {new_round_number}) ---")
    writer = get_stream_writer()  # Chainlit streaming
    writer({
               "msg": f"--- 🤔💭  Coordinating Agent is Setting Agenda for Round {new_round_number}/{state['max_rounds']} ---\n"})

    prompt = ChatPromptTemplate.from_messages([
        ("system", BASE_SYSTEM_PROMPT),
        ("human", AGENDA_PROMPT)
    ])

    chain = prompt | model | StrOutputParser()

    agenda = chain.invoke({
        "round_number": new_round_number,
        "max_rounds": state['max_rounds'],
        "subfields_str": ', '.join(state['subfields']),
        "snippet": sanitize_memory(state['human_input_snippet']),
        # "direction": state['human_input_direction'],
        "blackboard": sanitize_memory(state['blackboard'])
    })

    # Stream agenda to Chainlit
    print(f"--- New Agenda for Round {new_round_number} ---")
    print(agenda)
    msg = f"--- 📢 Coordinating Agent has set the following agenda for Round {new_round_number}/{state['max_rounds']} ---\n"
    msg += sanitize_memory(agenda)
    writer({"msg": msg})

    return {
        "current_agenda": agenda,
        "round_number": new_round_number,
        "new_proposals": []  # Reset new proposals for the round
    }


def scrutinize_and_update_node(state: GraphState) -> dict:
    """CA Node: Scrutinizes new proposals and updates shared memory."""
    print("--- Calling CA: Scrutinize and Update ---")
    writer = get_stream_writer()  # Chainlit streaming
    writer({
               "msg": f"--- 🧐🔍 Coordinating Agent is scrutinizing new proposals in Round {state['round_number']}/{state['max_rounds']} ---\n"})
    prompt = ChatPromptTemplate.from_messages([
        ("system", BASE_SYSTEM_PROMPT),
        ("human", SCRUTINIZE_PROMPT)
    ])
    chain = prompt | model.with_structured_output(ScrutinyResult)

    # Join the list of proposal strings into a single string
    new_proposals_str = "\n".join(state['new_proposals_xml'])

    response = chain.invoke({
        "round_number": state['round_number'],
        "max_rounds": state['max_rounds'],
        "agenda": sanitize_memory(state['current_agenda']),
        "snippet": sanitize_memory(state['human_input_snippet']),
        "subfields_str": ', '.join(state['subfields']),
        "new_proposals_str": sanitize_memory(new_proposals_str),
        "blackboard": sanitize_memory(state['blackboard'])
    })

    # Stream scrutiny results to Chainlit
    print("--- Scrutiny Results ---")
    blackboard = response.xml
    try:
        blackboard = render_xml_in_markdown(response.xml, title="Current Progress")
    except AssertionError as e:
        print(f"Error extracting current_progress: {e}")
    print(blackboard)

    msg = f"--- 📝 Coordinating Agent consolidated discussion after scrutiny in Round {state['round_number']}/{state['max_rounds']} ---\n"
    # msg += "Current Discussion Progress:\n"
    msg += sanitize_memory(blackboard)
    writer({"msg": msg})

    return {"blackboard": response.xml}


def generate_summary_node(state: GraphState) -> dict:
    """CA Node: Generates the final summary report."""
    print("--- Calling CA: Generate Final Summary ---")
    writer = get_stream_writer()  # Chainlit streaming
    writer({
               "msg": f"--- 🏁📝 Coordinating Agent is generating the final report after {state['round_number']} discussion rounds ---\n"})

    prompt = ChatPromptTemplate.from_messages([
        ("system", BASE_SYSTEM_PROMPT),
        ("human", SUMMARY_PROMPT)
    ])
    chain = prompt | model | StrOutputParser()

    summary = chain.invoke({
        "subfields_str": ', '.join(state['subfields']),
        "snippet": sanitize_memory(state['human_input_snippet']),
        "blackboard": sanitize_memory(state['blackboard'])
    })

    # Stream final summary to Chainlit
    print("--- Final Summary ---")
    summary = sanitize_memory(summary)
    print(summary)

    msg = f"--- 🏆🎉⭐✨🌟 Coordinating agent generated final report after {state['round_number']} discussion rounds  ---\n"
    msg += sanitize_memory(summary)
    writer({"msg": msg})

    return {"final_summary": summary}