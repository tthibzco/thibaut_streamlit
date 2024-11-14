import streamlit as st
import openai
from openai import OpenAI
import pandas as pd
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timezone


###### --------- Classes
class ProblemExtraction(BaseModel):
    person2: str
    relationship: str
    issues: list[str]
    context: str
    causes: list[str]
    desired_outcomes: list[str]

class YesNoAnswer(BaseModel):
    YesNo: bool

class ActionChosen(BaseModel):
    user_chosen_action_person_to_perform: str
    user_chosen_action_action_to_perform: str

# Initialize Firebase app
if not firebase_admin._apps:
    # Extract Firebase credentials from st.secrets
    firebase_credentials = {
        "type": st.secrets["firebase"]["type"],
        "project_id": st.secrets["firebase"]["project_id"],
        "private_key_id": st.secrets["firebase"]["private_key_id"],
        # Replace '\\n' with '\n' in private key
        "private_key": st.secrets["firebase"]["private_key"].replace('\\n', '\n'),
        "client_email": st.secrets["firebase"]["client_email"],
        "client_id": st.secrets["firebase"]["client_id"],
        "auth_uri": st.secrets["firebase"]["auth_uri"],
        "token_uri": st.secrets["firebase"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["firebase"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["firebase"]["client_x509_cert_url"],
    }
    cred = credentials.Certificate(firebase_credentials)
    firebase_admin.initialize_app(cred)
# Initialize Firestore database
db = firestore.client()


###### --------- Functions
# Initialization function
def ini():
    
    ###### --------- Global
    #global suggest_prompt, propose_prompt
    
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    code_assistant_setup = st.secrets["CODE_ASSISTANT_SETUP"] 
    code_assistant_setup2 = st.secrets["CODE_ASSISTANT_SETUP2"] 
    script_yesno_setup = st.secrets["YESNO_SETUP"]

    general_flow = {
        'Stage_id': [1, 2, 3],
        'Stage_name': ['Understanding', 'Suggesting solutions', 'Preparing execution'],
        'Stage_chat': ['', '', ''],
        'Stage_bot_validation': [False, False, False],
        'Stage_user_validation': [False, False, False],
        'Stage_user_function': ['understand_problem', 'suggest_solutions', 'prep_exec']
        }

    ###### --------- Variables
    # Initialize flags and variables
    if "convo1" not in st.session_state:
        st.session_state["convo1"] = []

    if "i1" not in st.session_state:
        st.session_state["i1"] = 1

    if "s1" not in st.session_state:
        st.session_state["s1"] = 1

    if "user_flow" not in st.session_state:
        st.session_state["user_flow"] = pd.DataFrame(general_flow)
    st.session_state["user_flow"].index = pd.RangeIndex(start=1, stop=len(st.session_state["user_flow"]) + 1, step=1)
    st.session_state["user_flow"]['Stage_chat'][st.session_state["s1"]]=st.session_state["convo1"]
    

    if "model_user1" not in st.session_state:
        st.session_state["model_user1"]=st.secrets["MODEL_USER1"]

    if "model_parsing1" not in st.session_state:
       st.session_state["model_parsing1"]=st.secrets["MODEL_PARSING1"]

    if "message_assistant" not in st.session_state:
        st.session_state["message_assistant"]=[{"role": "system", "content": code_assistant_setup}]

    if "message_assistant2" not in st.session_state:
        st.session_state["message_assistant2"]=[{"role": "system", "content": code_assistant_setup2}]

    if "yesno_setup" not in st.session_state:
        st.session_state["yesno_setup"]=[{"role": "system", "content": script_yesno_setup}]

    if "user_problem" not in st.session_state:
        st.session_state["user_problem"]=ProblemExtraction(person2="",relationship="",issues=[],context="",causes=[],desired_outcomes=[])
    
    if "y" not in st.session_state:
        st.session_state["y"]=0

    if "current_action" not in st.session_state:
        st.session_state["current_action"]=ActionChosen(user_chosen_action_action_to_perform='',user_chosen_action_person_to_perform='')
    

    #opening_prompt="Hello! I am here to help you with an interpersonal problem.\n Can you please describe it?\n"
    ###### --------- Visuals settings
    
    #st.session_state.messages.append({"role": "assistant", "content": opening_prompt})

#Function to move to another state
def transition_state():
    st.session_state.s1+=1
    st.session_state.i1=1
    st.session_state.convo1 = []

# Function for ChatGPT to paraphrase the problem
def understand_problem(whole_convo, model_user, model_parsing):

    if st.session_state.i1==1:
       chatGPT_setup_understanding = st.secrets["UNDERSTANDING"] 
       temp=whole_convo[-1]
       whole_convo.pop()
       whole_convo.append({"role": "system", "content": chatGPT_setup_understanding})
       whole_convo.append(temp)

    ###### --------- ChatGPTopening chat
    try:
        if st.session_state.user_flow['Stage_bot_validation'][st.session_state.s1]:
            yesno_eval = openai.beta.chat.completions.parse(
                model=model_parsing,
                n=1, #important to keep the number of choices limited to 1
                messages= st.session_state.yesno_setup + [whole_convo[-1]],
                response_format=YesNoAnswer
            )
            user_confirms = yesno_eval.choices[0].message
            if user_confirms.parsed:
                yesno_object=yesno_eval.choices[0].message.parsed
            else:
                print("Parsing refusal:", resp_parsing.refusal)
            st.session_state.user_flow['Stage_user_validation'][st.session_state.s1]=yesno_object.YesNo
            if yesno_object.YesNo:
                resp1 = "Thank you for confirming. Let's explore some possible solutions together."
                whole_convo.append({'role': 'assistant', 'content': resp1})
                st.session_state.messages.append({'role': 'assistant', 'content': resp1})
                save_message(st.session_state['user_name'], "assistant", resp1)
                transition_state()
                return (suggest_solutions(st.session_state.convo1, st.session_state.model_user1, st.session_state.model_parsing1))
            else:
                st.session_state.user_flow['Stage_bot_validation'][st.session_state.s1] = False
                resp1 = "Can you please specify what is incorrect in my understanding?"
                whole_convo.append({'role': 'assistant', 'content': resp1})
                return resp1
        else:
            response = openai.beta.chat.completions.parse(
                model=model_parsing,
                n=1, #important to keep the number of choices limited to 1
                messages=st.session_state.message_assistant+whole_convo[1:],
                response_format=ProblemExtraction
            )
            resp_parsing=response.choices[0].message
            if resp_parsing.parsed:
                st.session_state.user_problem=response.choices[0].message.parsed
            else:
                print("Parsing refusal:", resp_parsing.refusal)
            if are_all_properties_populated(st.session_state.user_problem):
                st.session_state.user_flow['Stage_bot_validation'][st.session_state.s1]=True
                resp1 = f"I understand that " + problem_summary(st.session_state.user_problem) + f"\n\nIs this correct?"
            else:
                response_foruser = openai.chat.completions.create(
                    model=model_user,
                    n=1, #important to keep the number of choices limited to 1
                    messages=whole_convo
                )
                resp1 = response_foruser.choices[0].message.content
        whole_convo.append({'role':'assistant', 'content':resp1})
        # Return the assistant's response using dot notation
        return resp1
    except Exception as e:
        return f"An error occurred: {e}"

# Function generating a summary of a problem
def problem_summary(problem: ProblemExtraction):
    summary = f"the problem is with {problem.person2}, who is a {problem.relationship.lower()} ."
    issues_str = ', '.join(problem.issues)
    summary += f" The issues are: {issues_str.lower()}."
    summary += f" This is happening in the context of {problem.context.lower()}."
    causes_str = ', '.join(problem.causes)
    summary += f" The causes are: {causes_str.lower()}."
    outcomes_str = ', '.join(problem.desired_outcomes)
    summary += f" The desired outcomes are: {outcomes_str.lower()}."
    return(summary)

# Function used to suggest actions to the user
def suggest_solutions(whole_convo, model_user, model_parsing):
    
    #propose_prompt="Thank you for choosing this action. Do you want to go in the details of it?"

    if st.session_state.i1 == 1:
        chatGPT_setup_suggesting_solutions= st.secrets["SUGGESTING"] 
        whole_convo.append({"role": "system", "content": chatGPT_setup_suggesting_solutions})
        whole_convo.append({"role": "system", "content": "The summary of the problem is " + problem_summary(st.session_state.user_problem)})
        whole_convo.append({"role": "user", "content": "What is your best suggestion?"})
        st.session_state.y= len(whole_convo) - 1

    try:
        if st.session_state.user_flow['Stage_bot_validation'][st.session_state.s1]:
            yesno_eval = openai.beta.chat.completions.parse(
                model=model_parsing,
                n=1, #important to keep the number of choices limited to 1
                messages= st.session_state.yesno_setup + [whole_convo[-1]],
                response_format=YesNoAnswer
            )
            user_confirms = yesno_eval.choices[0].message
            if user_confirms.parsed:
                yesno_object=user_confirms.parsed
            else:
                print("Parsing refusal:", resp_parsing.refusal)

            st.session_state.user_flow['Stage_user_validation'][st.session_state.s1]=yesno_object.YesNo
            if yesno_object.YesNo:
                resp1 = "Great! Let's proceed to prepare the execution of this action."
                whole_convo.append({'role': 'assistant', 'content': resp1})
                st.session_state.messages.append({'role': 'assistant', 'content': resp1})
                save_message(st.session_state['user_name'], "assistant", resp1)
                transition_state()
                return prep_exec(st.session_state.convo1, st.session_state.model_user1, st.session_state.model_parsing1)
            else:
                st.session_state.user_flow['Stage_bot_validation'][st.session_state.s1] = False
                st.session_state.current_action.user_chosen_action_person_to_perform =''
                st.session_state.current_action.user_chosen_action_action_to_perform =''
                st.session_state.y = len(whole_convo)
                response_foruser = openai.chat.completions.create(
                    model=model_user,
                    n=1, #important to keep the number of choices limited to 1
                    messages=whole_convo
                )
                resp1 = response_foruser.choices[0].message.content
                whole_convo.append({'role':'assistant', 'content':resp1})
                return resp1
        else:
            response = openai.beta.chat.completions.parse(
                model=model_parsing,
                n=1, #important to keep the number of choices limited to 1
                messages=st.session_state.message_assistant2+whole_convo[st.session_state.y:], #Original
                response_format=ActionChosen
            )
            resp_parsing=response.choices[0].message
            if resp_parsing.parsed:
                st.session_state.current_action=resp_parsing.parsed
            else:
                print("Parsing refusal:", resp_parsing.refusal)

            if are_all_properties_populated(st.session_state.current_action):
                st.session_state.user_flow['Stage_bot_validation'][st.session_state.s1]=True
                resp1 = f"I understand that you want " + action_summary(st.session_state.current_action) + f" Is this correct?"

            else:
                response_foruser = openai.chat.completions.create(
                    model=model_user,
                    n=1, #important to keep the number of choices limited to 1
                    messages=whole_convo
                )
                resp1 = response_foruser.choices[0].message.content
        
        whole_convo.append({'role':'assistant', 'content':resp1})
        return resp1

    except Exception as e:
        return f"An error occurred: {e}"

# Function summarizing the action chosen
def action_summary(action1):
    sum1 = action1.user_chosen_action_person_to_perform.lower() + f" to " + action1.user_chosen_action_action_to_perform.lower()
    return sum1

# Function used to execute the solution
def prep_exec(whole_convo, model_user, model_parsing):

    if st.session_state.i1 == 1:
        #temp = whole_convo[-1]["content"]
        #whole_convo.pop()

        if st.session_state.current_action.user_chosen_action_person_to_perform=='me':
            chatGPT_setup_prep_execution= st.secrets["EXECUTING1"] 
            whole_convo.append({"role": "system", "content": chatGPT_setup_prep_execution})
            whole_convo.append({"role": "system", "content": "The problem is " + problem_summary(st.session_state.user_problem)})
            whole_convo.append({"role": "user", "content": "What email are you thinking you will send?"})
        else:
            chatGPT_setup_prep_execution= st.secrets["EXECUTING2"] 
            whole_convo.append({"role": "system", "content": chatGPT_setup_prep_execution})
            whole_convo.append({"role": "system", "content": "The action is " + action_summary(st.session_state.current_action)})
            whole_convo.append({"role": "user", "content": "How can this be done?"})
        try:
            response_foruser = openai.chat.completions.create(
                model=model_user,
                n=1, #important to keep the number of choices limited to 1
                messages=whole_convo
                )
            resp1 = response_foruser.choices[0].message.content
            whole_convo.append({'role':'assistant', 'content':resp1})
            return resp1
        except Exception as e:
            return f"An error occurred: {e}"
    else:
        yesno_eval = openai.beta.chat.completions.parse(
            model=model_parsing,
            n=1, #important to keep the number of choices limited to 1
            messages= st.session_state.yesno_setup + [whole_convo[-1]],
            response_format=YesNoAnswer
        )
        user_confirms = yesno_eval.choices[0].message
        if user_confirms.parsed:
            yesno_object=yesno_eval.choices[0].message.parsed
        else:
            print("Parsing refusal:", user_confirms.refusal)

        st.session_state.user_flow['Stage_user_validation'][st.session_state.s1]=yesno_object.YesNo
        if yesno_object.YesNo:
            if st.session_state.current_action.user_chosen_action_person_to_perform.lower() == 'me':
                resp1 = "Thank you for validating the content. I let you know when I've done it"
            else:
                resp1 = "Thank you for validating the content. I will wait for your follow up"
        else:
            try:
                response_foruser = openai.chat.completions.create(
                    model=model_user,
                    n=1, #important to keep the number of choices limited to 1
                    messages=whole_convo
                )
                resp1 = response_foruser.choices[0].message.content
            except Exception as e:
                return f"An error occurred: {e}"
        whole_convo.append({'role':'assistant', 'content':resp1})
    return resp1

# Function to handle the user submission
def submit_message(prompt1):
    # User's message
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.convo1.append({"role": "user", "content": prompt})
    save_message(st.session_state['user_name'], "User", prompt)

    # Assistan's response
    GPT_response = globals()[st.session_state.user_flow['Stage_user_function'][st.session_state.s1]](st.session_state.convo1, st.session_state.model_user1, st.session_state.model_parsing1)
    if GPT_response:
        st.session_state.messages.append({"role": "assistant", "content": GPT_response})
        save_message(st.session_state['user_name'], "assistant", GPT_response)
    st.session_state.i1 += 1


    #if st.session_state.user_flow['Stage_bot_validation'][st.session_state.s1] and st.session_state.user_flow['Stage_user_validation'][st.session_state.s1]:
    #    transition_state()
    #else:
        # No input from the user
    #    pass

# Save Message in the DB
def save_message(user_name, role, content):
    # Prepare message data
    message_data = {
        'user_name': user_name,
        'role': role,
        'content': content,
        'date': datetime.now(timezone.utc)  # Use UTC time
    }
    # Add to Firestore
    db.collection('messages').add(message_data)

# Tests if all properties of an object are populated
def are_all_properties_populated(obj):
    return all(value for value in vars(obj).values())

st.title("Prototype: BuildPath Assitant")

###### --------- Main program
if "messages" not in st.session_state:
    st.session_state["messages"]=[]
    ini()

# Initialize user_name and name_greeted in session_state
if "user_name" not in st.session_state:
    st.session_state["user_name"] = ""
if "name_greeted" not in st.session_state:
    st.session_state["name_greeted"] = False

if not st.session_state["name_greeted"]:
    user_name_input = st.text_input("Welcome, can you please tell me your name?")
    if user_name_input:
        st.session_state["user_name"] = user_name_input
        opening_prompt = f"Hello {st.session_state['user_name']}! I am BuildPath, I will help you with an interpersonal problem.\nCan you please describe it?\n"
        st.session_state.messages.append({"role": "assistant", "content": opening_prompt})
        st.session_state["name_greeted"] = True
    else:
        st.stop()

if prompt := st.chat_input("Type here"):
    submit_message(prompt)

for message in st.session_state.messages:
     with st.chat_message(message["role"]):
         st.markdown(message["content"])