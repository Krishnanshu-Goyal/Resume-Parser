from hugchat import hugchat
from hugchat.login import Login
import re

EMAIL = "" #add your hugface login id
PASSWD = ""  #add your hugface login password
cookie_path_dir = "./cookies/"

def get_data(data):
    try:
        sign = Login(EMAIL, PASSWD)
        cookies = sign.login(cookie_dir_path=cookie_path_dir, save_cookies=True)
        chatbot = hugchat.ChatBot(cookies=cookies.get_dict())
    except Exception as e:
        raise Exception(f"Failed to initialize chatbot: {e}")

    prompt = f"extract  name, emailid, mobile_number, skills, country, state, city,degree,University,Projects,Certifications,Hobbies,Interest,Achievements,experience, intern, actual skills from {data}"
    query_result = str(chatbot.query(prompt, web_search=True))
   
    return query_result