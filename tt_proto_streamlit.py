import streamlit as st
import openai
from openai import OpenAI
import pandas as pd
from pydantic import BaseModel

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

###### --------- Functions
# Initialization function
def ini():
    
    ###### --------- Global
    global suggest_prompt, propose_prompt
    
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
    

    opening_prompt="Hello! I am here to help you with an interpersonal problem.\n Can you please describe it?\n"
    
    ###### --------- Visuals settings
    st.session_state.messages.append({"role": "assistant", "content": opening_prompt})

#Function to move to another state
def transition_state():
    st.session_state.s1+=1
    st.session_state.i1=1
    st.session_state.convo1 = []

# Function for ChatGPT to paraphrase the problem
def understand_problem(whole_convo, model_user, model_parsing):

    suggest_prompt="Thank you for confirming my understanding. Are you ok with me suggesting a few solutions?"

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
                resp1 = suggest_prompt
            else:
                st.session_state.user_flow['Stage_bot_validation'][st.session_state.s1] = False
                resp1 = "Can you please specify what is incorrect in my understanding?"
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
                resp1 = f"I understand that " + problem_summary(st.session_state.user_problem) + f"\nIs this correct?"
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
    
    propose_prompt="Thank you for choosing this action. Do you want to go in the details of it?"

    if st.session_state.i1 == 1:
        chatGPT_setup_suggesting_solutions= st.secrets["SUGGESTING"] 
        
        temp = whole_convo[-1]["content"]
        whole_convo.pop()
        whole_convo.append({"role": "system", "content": chatGPT_setup_suggesting_solutions})
        whole_convo.append({"role": "system", "content": "The summary of the problem is " + problem_summary(st.session_state.user_problem)})
        whole_convo.append({"role": "user", "content": temp + " What is your best suggestion?"})
        st.session_state.y= 2 

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
                resp1 = propose_prompt
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
        else:
            response = openai.beta.chat.completions.parse(
            model=model_parsing,
            n=1, #important to keep the number of choices limited to 1
            messages=st.session_state.message_assistant2+whole_convo[st.session_state.y:], #Original
            response_format=ActionChosen
            )
            resp_parsing=response.choices[0].message
            if resp_parsing.parsed:
                st.session_state.current_action=response.choices[0].message.parsed
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

    except Exception as e:
        return f"An error occurred: {e}"
    return resp1

# Function summarizing the action chosen
def action_summary(action1):
    sum1 = action1.user_chosen_action_person_to_perform.lower() + f" to " + action1.user_chosen_action_action_to_perform.lower()
    return sum1

# Function used to execute the solution
def prep_exec(whole_convo, model_user, model_parsing):

    if st.session_state.i1 == 1:
        temp = whole_convo[-1]["content"]
        whole_convo.pop()

        if st.session_state.current_action.user_chosen_action_person_to_perform=='me':
            chatGPT_setup_prep_execution= st.secrets["EXECUTING1"] 
        else:
            chatGPT_setup_prep_execution= st.secrets["EXECUTING2"] 
        
        whole_convo.append({"role": "system", "content": chatGPT_setup_prep_execution})
        if st.session_state.current_action.user_chosen_action_person_to_perform=='me':
            whole_convo.append({"role": "system", "content": "The problem is " + problem_summary(st.session_state.user_problem)})
            whole_convo.append({"role": "user", "content": "What email are you thinking you will send?"})
        else:
            whole_convo.append({"role": "system", "content": "The action is " + action_summary(st.session_state.current_action)})
            whole_convo.append({"role": "user", "content": temp + ". How can this be done?"})
        try:
            response_foruser = openai.chat.completions.create(
                model=model_user,
                n=1, #important to keep the number of choices limited to 1
                messages=whole_convo
                )
            resp1 = response_foruser.choices[0].message.content
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

    st.session_state.messages.append({"role": "user", "content": prompt})

    st.session_state.convo1.append({"role": "user", "content": prompt})
    GPT_response = globals()[st.session_state.user_flow['Stage_user_function'][st.session_state.s1]](st.session_state.convo1, st.session_state.model_user1, st.session_state.model_parsing1)
    st.session_state.messages.append({"role": "assistant", "content": GPT_response})
    st.session_state.i1 += 1

    if st.session_state.user_flow['Stage_bot_validation'][st.session_state.s1] and st.session_state.user_flow['Stage_user_validation'][st.session_state.s1]:
        transition_state()
    else:
        # No input from the user
        pass

# Tests if all properties of an object are populated
def are_all_properties_populated(obj):
    return all(value for value in vars(obj).values())

st.title("Prototype Thibz BuildPath Interface")

###### --------- Main program
if "messages" not in st.session_state:
    st.session_state["messages"]=[]
    ini()

if prompt := st.chat_input("Type here"):
    submit_message(prompt)

for message in st.session_state.messages:
     with st.chat_message(message["role"]):
         st.markdown(message["content"])