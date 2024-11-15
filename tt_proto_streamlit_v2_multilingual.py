import streamlit as st
import openai
from openai import OpenAI
import pandas as pd
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timezone
import langid  # Added import for language detection

###### --------- Messages Translations
messages_translations = {
    'thank_you_confirming': {
        'en': 'Thank you for confirming. Let\'s explore some possible solutions together.',
        'fr': 'Merci pour votre confirmation. Explorons ensemble quelques solutions possibles.',
        'de': 'Danke für die Bestätigung. Lassen Sie uns gemeinsam einige mögliche Lösungen finden.',
        'es': 'Gracias por confirmar. Exploremos juntos algunas posibles soluciones.'
    },
    'specify_incorrect_understanding': {
        'en': 'Can you please specify what is incorrect in my understanding?',
        'fr': 'Pourriez-vous préciser ce qui est incorrect dans ma compréhension ?',
        'de': 'Können Sie bitte angeben, was an meinem Verständnis falsch ist?',
        'es': '¿Puede especificar qué es incorrecto en mi comprensión?'
    },
    'awesome_move_forward': {
        'en': 'Awesome! Let\'s move forward and make it happen.',
        'fr': 'Formidable ! Avançons et mettons cela en oeuvre.',
        'de': 'Großartig! Lassen Sie uns weitermachen und an den Lösungen arbeiten.',
        'es': '¡Genial! Sigamos adelante y hagámoslo realidad.'
    },
    'i_understand_that_problem': {
        'en': 'I understand that {problem_summary}  \n\nIs this correct?',
        'fr': 'Je comprends que {problem_summary}  \n\nEst-ce correct ?',
        'de': 'Ich verstehe, dass {problem_summary}  \n\nIst das korrekt?',
        'es': 'Entiendo que {problem_summary}  \n\n¿Es correcto?'
    },
    'thank_you_validating_content_done': {
        'en': 'Thank you for validating the content. I will let you know when I\'ve done it.',
        'fr': 'Merci d\'avoir validé le contenu. Je vous informerai quand cela sera fait.',
        'de': 'Danke, dass Sie den Inhalt bestätigt haben. Ich lasse Sie wissen, wenn ich es erledigt habe.',
        'es': 'Gracias por validar el contenido. Te avisaré cuando lo haya hecho.'
    },
    'thank_you_validating_content_wait': {
        'en': 'Thank you for validating the content. I will wait for your follow-up.',
        'fr': 'Merci d\'avoir validé le contenu. J\'attends votre suivi.',
        'de': 'Danke, dass Sie den Inhalt bestätigt haben. Ich werde auf Ihre Rückmeldung warten.',
        'es': 'Gracias por validar el contenido. Esperaré tu seguimiento.'
    },
    'what_email_thinking_send': {
        'en': 'What email are you thinking you will send?',
        'fr': 'Quel email pensez-vous envoyer ?',
        'de': 'Welche E-Mail denken Sie zu senden?',
        'es': '¿Qué correo electrónico estás pensando en enviar?'
    },
    'how_can_this_be_done': {
        'en': 'How can this be done?',
        'fr': 'Comment cela peut-il être fait ?',
        'de': 'Wie kann das realisiert werden?',
        'es': '¿Cómo se puede hacer esto?'
    },
    'welcome_ask_name': {
        'en': 'Welcome, can you please tell me your name?',
        'fr': 'Bienvenue, pouvez-vous me dire votre nom s\'il vous plaît ?',
        'de': 'Willkommen, können Sie mir bitte Ihren Namen sagen?',
        'es': 'Bienvenido, ¿puedes decirme tu nombre por favor?'
    },
    'hello_name_introduction': {
        'en': 'Hello {name}! I am BuildPath, I will help you with an interpersonal problem. Can you please describe it?\n',
        'fr': 'Bonjour {name} ! Je suis BuildPath, je vais vous aider avec un problème interpersonnel. Pouvez-vous le décrire s\'il vous plaît ?\n',
        'de': 'Hallo {name}! Ich bin BuildPath, ich helfe Ihnen bei einem zwischenmenschlichen Problem. Können Sie es bitte beschreiben?\n',
        'es': '¡Hola {name}! Soy BuildPath, te ayudaré con un problema interpersonal. ¿Puedes describirlo, por favor?\n'
    },
    'understand_intro': {
        'en': "I understand that",
        'fr': "Je comprends que",
        'de': "Ich verstehe, dass",
        'es': "Entiendo que"
    },
    'is_correct': {
        'en': "Is this correct?",
        'fr': "Est-ce correct ?",
        'de': "Ist das korrekt?",
        'es': "¿Es correcto?"
    },
    'summary_1': {
        'en': "The problem is with {person}, who is a {relationship}.",
        'fr': "Le problème intervient avec {person}, qui est un(e) {relationship}.",
        'de': "Das Problem ist mit {person}, der/die ein(e) {relationship} ist.",
        'es': "El problema es con {person}, quien es un(a) {relationship}."
    },
    'summary_2': {
        'en': "The issues are: {issues}.",
        'fr': "Les problèmes sont : {issues}.",
        'de': "Die Probleme sind: {issues}.",
        'es': "Los problemas son: {issues}."
    },
    'summary_3': {
        'en': "This is happening in the context of: {context}.",
        'fr': "Cela se produit dans le contexte de : {context}.",
        'de': "Dies geschieht im Kontext von: {context}.",
        'es': "Esto sucede en el contexto de: {context}."
    },
    'summary_4': {
        'en': "The causes are: {causes}.",
        'fr': "Les causes sont : {causes}.",
        'de': "Die Ursachen sind: {causes}.",
        'es': "Las causas son: {causes}."
    },
    'summary_5': {
        'en': "The desired outcomes are: {outcomes}.",
        'fr': "Les résultats souhaités sont : {outcomes}.",
        'de': "Die gewünschten Ergebnisse sind: {outcomes}.",
        'es': "Los resultados deseados son: {outcomes}."
    },
    'action_self_full': {
        'en': "I understand that you want me to {action}. Is this correct?",
        'fr': "Je comprends que vous voulez que je(j') {action}. Est-ce correct ?",
        'de': "Ich verstehe, dass Sie {action} möchten. Ist das korrekt?",
        'es': "Entiendo que quieres {action}. ¿Es correcto?"
    },
    'action_other_full': {
        'en': "I understand that you want to {action}. Is this correct?",
        'fr': "Je comprends que vous voulez {action}. Est-ce correct ?",
        'de': "Ich verstehe, dass Sie möchten {action}. Ist das korrekt?",
        'es': "Entiendo que quieres {action}. ¿Es correcto?"
    },
    'action_summary_template': {
        'en': "{person} to {action}",
        'fr': "{person} à {action}",
        'de': "{person} zu {action}",
        'es': "{person} a {action}"
    },
}

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
    
    # Initialize detected_language if not already set
    if 'detected_language' not in st.session_state:
        st.session_state['detected_language'] = None

    ###### --------- Visuals settings
    
    #st.session_state.messages.append({"role": "assistant", "content": opening_prompt})

# Function to move to another state
def transition_state():
    st.session_state.s1+=1
    st.session_state.i1=1
    st.session_state.convo1 = []

# Function for ChatGPT to paraphrase the problem
def understand_problem(whole_convo, model_user, model_parsing):

    if st.session_state.i1==1:
       # Detect language
       user_message = whole_convo[-1]['content']
       lang, confidence = langid.classify(user_message)
       if lang not in ['en', 'fr', 'de', 'es']: 
           lang = 'en'  # default to English
       st.session_state['detected_language'] = lang

       chatGPT_setup_understanding = st.secrets["UNDERSTANDING"] 
       temp=whole_convo[-1]
       whole_convo.pop()
       whole_convo.append({"role": "system", "content": chatGPT_setup_understanding})
       whole_convo.append(temp)

    ###### --------- ChatGPT opening chat
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
                resp1 = get_translated_message('thank_you_confirming')
                whole_convo.append({'role': 'assistant', 'content': resp1})
                st.session_state.messages.append({'role': 'assistant', 'content': resp1})
                save_message(st.session_state['user_name'], "assistant", resp1)
                transition_state()
                return (suggest_solutions(st.session_state.convo1, st.session_state.model_user1, st.session_state.model_parsing1))
            else:
                st.session_state.user_flow['Stage_bot_validation'][st.session_state.s1] = False
                resp1 = get_translated_message('specify_incorrect_understanding')
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
                intro = get_translated_message('understand_intro')
                summary = problem_summary(st.session_state.user_problem)
                confirmation = get_translated_message('is_correct')
                resp1 = f"{intro} {summary} {confirmation}"                
            else:
                response_foruser = openai.chat.completions.create(
                    model=model_user,
                    n=1, #important to keep the number of choices limited to 1
                    messages=whole_convo
                )
                resp1 = response_foruser.choices[0].message.content
        whole_convo.append({'role':'assistant', 'content':resp1})
        # Return the assistant's response
        return resp1
    except Exception as e:
        return f"An error occurred: {e}"

# Function generating a summary of a problem
def problem_summary(problem: ProblemExtraction):
    summary = get_translated_message(
        'summary_1',
        person=problem.person2,
        relationship=problem.relationship.lower()
    )
    issues_str = ', '.join(problem.issues).lower()
    summary += " " + get_translated_message('summary_2', issues=issues_str)
    summary += " " + get_translated_message('summary_3', context=problem.context.lower())
    causes_str = ', '.join(problem.causes).lower()
    summary += " " + get_translated_message('summary_4', causes=causes_str)
    outcomes_str = ', '.join(problem.desired_outcomes).lower()
    summary += " " + get_translated_message('summary_5', outcomes=outcomes_str)
    return summary


# Function used to suggest actions to the user
def suggest_solutions(whole_convo, model_user, model_parsing):
    
    if st.session_state.i1 == 1:
        chatGPT_setup_suggesting_solutions= st.secrets["SUGGESTING"] 

        # Add language directive to the prompt
        detected_language = st.session_state.get('detected_language', 'en')
        language_instruction = f"Please answer in language :{detected_language}."
        # Combine the hardcoded prompt with the language instruction
        whole_convo.append({"role": "system", "content": chatGPT_setup_suggesting_solutions})
        whole_convo.append({"role": "system", "content": language_instruction})
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
                resp1 = get_translated_message('awesome_move_forward')
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
                #resp1 = f"I understand that you want " + action_summary(st.session_state.current_action) + f" Is this correct?"
                # Determine which template to use
                if st.session_state.current_action.user_chosen_action_person_to_perform.lower() == 'me':
                    template_key = 'action_self_full'
                    action_text = st.session_state.current_action.user_chosen_action_action_to_perform.lower()
                    resp1 = get_translated_message(template_key, action=action_text)
                else:
                    template_key = 'action_other_full'
                    person_text = st.session_state.current_action.user_chosen_action_person_to_perform.lower()
                    action_text = st.session_state.current_action.user_chosen_action_action_to_perform.lower()
                    resp1 = get_translated_message(template_key, action=action_text)
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

        if st.session_state.current_action.user_chosen_action_person_to_perform=='me':
            chatGPT_setup_prep_execution= st.secrets["EXECUTING1"] 
            whole_convo.append({"role": "system", "content": chatGPT_setup_prep_execution})
            whole_convo.append({"role": "system", "content": "The problem is " + problem_summary(st.session_state.user_problem)})
            whole_convo.append({"role": "user", "content": get_translated_message('what_email_thinking_send')})
        else:
            chatGPT_setup_prep_execution= st.secrets["EXECUTING2"] 
            whole_convo.append({"role": "system", "content": chatGPT_setup_prep_execution})
            whole_convo.append({"role": "system", "content": "The action is " + action_summary(st.session_state.current_action)})
            whole_convo.append({"role": "user", "content": get_translated_message('how_can_this_be_done')})
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
                resp1 = get_translated_message('thank_you_validating_content_done')
            else:
                resp1 = get_translated_message('thank_you_validating_content_wait')
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

    # Assistant's response
    GPT_response = globals()[st.session_state.user_flow['Stage_user_function'][st.session_state.s1]](st.session_state.convo1, st.session_state.model_user1, st.session_state.model_parsing1)
    if GPT_response:
        st.session_state.messages.append({"role": "assistant", "content": GPT_response})
        save_message(st.session_state['user_name'], "assistant", GPT_response)
    st.session_state.i1 += 1

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

def get_translated_message(message_key, **kwargs):
    allowed_languages = ['en', 'fr', 'de', 'es']
    lang = st.session_state.get('detected_language', 'en')
    if lang not in allowed_languages:
        lang = 'en'
    message_template = messages_translations[message_key].get(lang, messages_translations[message_key]['en'])
    return message_template.format(**kwargs)


st.title("Prototype: BuildPath Assistant")

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
    name_input_container = st.empty()
    user_name_input = name_input_container.text_input("Welcome, can you please tell me your name?")
    if user_name_input:
        st.session_state["user_name"] = user_name_input
        name_input_container.empty()
        opening_prompt = f"Hello {st.session_state['user_name']}! I am BuildPath, I will help you with an interpersonal problem. Can you please describe it?\n"
        st.session_state.messages.append({"role": "assistant", "content": opening_prompt})
        st.session_state["name_greeted"] = True
    else:
        st.stop()

if prompt := st.chat_input("Type here"):
    submit_message(prompt)

for message in st.session_state.messages:
     with st.chat_message(message["role"]):
         st.markdown(message["content"])
