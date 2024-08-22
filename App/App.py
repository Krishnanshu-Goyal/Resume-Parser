
###### Packages Used ######
import streamlit as st # core package used in this project
import pandas as pd
import base64, random
import time,datetime
import pymysql
import os
import socket
import platform
import fitz
import geocoder
import secrets
import io,random
import plotly.express as px # to create visualisations at the admin session
import plotly.graph_objects as go
from geopy.geocoders import Nominatim
# libraries used to parse the pdf files

from pdfminer3.layout import LAParams, LTTextBox
from pdfminer3.pdfpage import PDFPage
from pdfminer3.pdfinterp import PDFResourceManager
from pdfminer3.pdfinterp import PDFPageInterpreter
from pdfminer3.converter import TextConverter
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import re
from streamlit_tags import st_tags
from PIL import Image
import genai
# pre stored data for prediction purposes
from Courses import ds_course,web_course,android_course,ios_course,uiux_course,resume_videos,interview_videos
import nltk

from dotenv import load_dotenv

load_dotenv()
nltk.download('stopwords')


###### Preprocessing functions ######


# Generates a link allowing the data in a given panda dataframe to be downloaded in csv format 
def get_csv_download_link(df,filename,text):
    csv = df.to_csv(index=False)
    ## bytes conversions
    b64 = base64.b64encode(csv.encode()).decode()      
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'
    return href

def parse_resume(data):
    resume_text = {}
    current_key = None
    current_value = []
    data=data.replace("- ","\n")
    data=data.replace("**","\n")
    for line in data.split('\n'):
        if line.strip() == '':
            continue

        # Match lines that start with a key
        match = re.match(r'(\w[\w\s]*):\s*(.*)', line)
        if match:
            # Save the previous key-value pair
            if current_key and current_value:
                resume_text[current_key.lower()] = ' '.join(current_value).strip()

            # Start a new key-value pair
            current_key = match.group(1)
            current_value = [match.group(2)]
        else:
            # Append to the current value
            current_value.append(line.strip())

    # Save the last key-value pair
    if current_key and current_value:
        resume_text[current_key.lower()] = ' '.join(current_value).strip()
    # if "intern" in resume_text['experience']:
    #     resume_text['intern']=resume_text['intern']+resume_text['experience']
    return resume_text

def send_email(subject, body, to_email):
    from_email = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD")

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_email, password)
        text = msg.as_string()
        server.sendmail(from_email, to_email, text)
        server.quit()
        return "Email sent successfully!"
    except smtplib.SMTPAuthenticationError as e:
        return f"SMTPAuthenticationError: {e}"
    except Exception as e:
        return f"Error: {e}"

# Reads Pdf file and check_extractable
def pdf_reader(file):
    resource_manager = PDFResourceManager()
    fake_file_handle = io.StringIO()
    converter = TextConverter(resource_manager, fake_file_handle, laparams=LAParams())
    page_interpreter = PDFPageInterpreter(resource_manager, converter)
    with open(file, 'r', encoding='utf-8') as fh:
        for page in PDFPage.get_pages(fh,caching=True,check_extractable=True):
            page_interpreter.process_page(page)
            print(page)
        text = fake_file_handle.getvalue()

    ## close open handles
    converter.close()
    fake_file_handle.close()
    return text

def split_text_to_list(text):
    # Split the text by commas
    parts = [part.strip() for part in text.split(',')]
    return parts


def get_pdf_download_link(pdf_bytes):
    pdf_b64 = base64.b64encode(pdf_bytes).decode()
    href = f'<a href="data:application/pdf;base64,{pdf_b64}" download="file.pdf">Download PDF file</a>'
    return href



def show_pdf(file_path):
    try:
        with open(file_path, "rb") as f:
            pdf_bytes = f.read()
        st.markdown(get_pdf_download_link(pdf_bytes), unsafe_allow_html=True)
    except FileNotFoundError:
        st.error(f"File '{file_path}' not found.")




# course recommendations which has data already loaded from Courses.py
def course_recommender(course_list):
    st.subheader("Courses & Certificates Recommendations ")
    c = 0
    rec_course = []
    ## slider to choose from range 1-10
    no_of_reco = st.slider('Choose Number of Course Recommendations:', 1, 10, 5)
    random.shuffle(course_list)
    for c_name, c_link in course_list:
        c += 1
        st.markdown(f"({c}) [{c_name}]({c_link})")
        rec_course.append(c_name)
        if c == no_of_reco:
            break
    return rec_course


###### Database Stuffs ######


# sql connector
connection = pymysql.connect(host='localhost',user='root',password='root@MySQL4admin',db='cv')
cursor = connection.cursor()


# inserting miscellaneous data, fetched results, prediction and recommendation into user_data table
def insert_data(sec_token,ip_add,host_name,dev_user,os_name_ver,latlong,city,state,country,act_name,act_mail,act_mob,name,email,res_score,timestamp,no_of_pages,reco_field,cand_level,skills,recommended_skills,courses,pdf_name):
    DB_table_name = 'user_data'

    insert_sql = "insert into " + DB_table_name + """
    values (0,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
    rec_values = (str(sec_token),str(ip_add),host_name,dev_user,os_name_ver,str(latlong),city,state,country,act_name,act_mail,act_mob,name,email,str(res_score),timestamp,str(no_of_pages),reco_field,cand_level,skills,recommended_skills,courses,pdf_name)
    cursor.execute(insert_sql, rec_values)
    connection.commit()


# inserting feedback data into user_feedback table
def insertf_data(feed_name,feed_email,feed_score,comments,Timestamp):
    DBf_table_name = 'user_feedback'
    insertfeed_sql = "insert into " + DBf_table_name + """
    values (0,%s,%s,%s,%s,%s)"""
    rec_values = (feed_name, feed_email, feed_score, comments, Timestamp)
    cursor.execute(insertfeed_sql, rec_values)
    connection.commit()


###### Setting Page Configuration (favicon, Logo, Title) ######


st.set_page_config(
   page_title="AI Resume Analyzer",
   page_icon='./Logo/recommend.png',
)


###### Main function run() ######


def run():
    
    
    resume_score=0
    # Define the desired width and height
    image_width = 100
    image_height = 70
    bottom_padding = 30  # in pixels

    
    # Display the logo image using st.markdown
    st.markdown(image_html, unsafe_allow_html=True)
    image_path = "/Users/krish/Desktop/AI-Resume-Analyzer-main/App/Logo/RESUM.png"

    # Define the desired width and height
    
    top_padding = 80  # in pixels

    # Read and encode the image
    with open(image_path, "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode()

    # Use CSS to style the image and position it in the top right corner with bottom padding
    image_html = f"""
        <div style="position: center; padding-top: {top_padding}px; ">
            <img src="data:image/png;base64,{encoded_image}" ">
        </div>
    """

    # Display the logo image using st.markdown
    st.markdown(image_html, unsafe_allow_html=True)
    st.markdown('<style>background-color:black</style>',unsafe_allow_html=True)  
    st.sidebar.markdown("# Choose Something...")
    activities = ["User", "Feedback", "About", "Admin"]
    choice = st.sidebar.selectbox("Choose among the given options:", activities)
    link = '<b><a x style="text-decoration: none; color: white;">Ernst & Young</a></b>' 
    st.sidebar.markdown(link, unsafe_allow_html=True)
    
    ###### Creating Database and Table ######


    # Create the DB
    db_sql = """CREATE DATABASE IF NOT EXISTS CV;"""
    cursor.execute(db_sql)


    # Create table user_data and user_feedback
    DB_table_name = 'user_data'
    table_sql = "CREATE TABLE IF NOT EXISTS " + DB_table_name + """
                    (ID INT NOT NULL AUTO_INCREMENT,
                    sec_token varchar(20) NOT NULL,
                    ip_add varchar(50) NULL,
                    host_name varchar(50) NULL,
                    dev_user varchar(50) NULL,
                    os_name_ver varchar(50) NULL,
                    latlong varchar(50) NULL,
                    city varchar(50) NULL,
                    state varchar(50) NULL,
                    country varchar(50) NULL,
                    act_name varchar(50) NOT NULL,
                    act_mail varchar(50) NOT NULL,
                    act_mob varchar(20) NOT NULL,
                    Name varchar(500) NOT NULL,
                    Email_ID VARCHAR(500) NOT NULL,
                    resume_score VARCHAR(8) NOT NULL,
                    Timestamp VARCHAR(50) NOT NULL,
                    Page_no VARCHAR(5) NOT NULL,
                    Predicted_Field BLOB NOT NULL,
                    User_level BLOB NOT NULL,
                    Actual_skills BLOB NOT NULL,
                    Recommended_skills BLOB NOT NULL,
                    Recommended_courses BLOB NOT NULL,
                    pdf_name varchar(50) NOT NULL,
                    PRIMARY KEY (ID)
                    );
                """
    cursor.execute(table_sql)


    DBf_table_name = 'user_feedback'
    tablef_sql = "CREATE TABLE IF NOT EXISTS " + DBf_table_name + """
                    (ID INT NOT NULL AUTO_INCREMENT,
                        feed_name varchar(50) NOT NULL,
                        feed_email VARCHAR(50) NOT NULL,
                        feed_score VARCHAR(5) NOT NULL,
                        comments VARCHAR(100) NULL,
                        Timestamp VARCHAR(50) NOT NULL,
                        PRIMARY KEY (ID)
                    );
                """
    cursor.execute(tablef_sql)


    ###### CODE FOR CLIENT SIDE (USER) ######

    if choice == 'User':
        
        # Collecting Miscellaneous Information
        act_name = st.text_input('Name*')
        act_mail = st.text_input('Mail*')
        act_mob  = st.text_input('Mobile Number*')
        
        act_city  = st.text_input('City*')
        act_state  = st.text_input('State*')
        sec_token = secrets.token_urlsafe(12)
        host_name = socket.gethostname()
        ip_add = socket.gethostbyname(host_name)
        dev_user = os.getlogin()
        os_name_ver = platform.system() + " " + platform.release()
        g = geocoder.ip('me')
        latlong = g.latlng
        geolocator = Nominatim(user_agent="http")
        location = geolocator.reverse(latlong, language='en')
        address = location.raw['address']
        cityy = address.get('city', '')
        statee = address.get('state', '')
        countryy = address.get('country', '')  
        city = cityy
        state = statee
        country = countryy


        # Upload Resume
        st.markdown('''<h5 style='text-align: left; color: grey;'> Upload Your Resume, And Get Smart Recommendations</h5>''',unsafe_allow_html=True)
        

        def save_uploaded_resume(pdf_file):
            save_image_path = os.path.join('/Users/krish/Desktop/AI-Resume-Analyzer-main/App/Uploaded_Resumes/', pdf_file.name)
            with open(save_image_path, "wb") as f:
                f.write(pdf_file.getbuffer())
            return save_image_path

# Function to extract text from PDF using PyMuPDF
        def extract_text_from_pdf(pdf_path):
            text = ""
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text += page.get_text()
            #st.text(text)
            return text

# Main Streamlit code
        pdf_file = st.file_uploader("Choose your Resume", type=["pdf"])
        if pdf_file is not None:
            with st.spinner('Hang On While We Cook Magic For You...'):
                time.sleep(4)
            
            # Save the uploaded resume to a folder
            save_image_path = save_uploaded_resume(pdf_file)
            pdf_name = pdf_file.name
            
            # Initialize resume_data to None
            resume_data = None
            
            # Extract text from PDF using PyMuPDF
            pdf_text = extract_text_from_pdf(save_image_path)
                
                # Pass extracted text to ResumeParser
            try:
                resume_data=genai.get_data(pdf_text)
            except:
                resume_data=genai.get_data(pdf_text)
                
            
            
            
            if resume_data is None:
                st.error("Failed to extract data from the resume. Please try again with a different file.")
            else:
                pass
                
          
            
            resume_text={}
            # Now you can safely check if resume_data exists and use it
            if resume_data:
                
                resume_text = parse_resume(resume_data)
                resume_text['name']=resume_text.get('name') or resume_text.get('Name')
                resume_text['number']=resume_text.get('number') or resume_text.get('Number') or resume_text.get('Mobile Number') or resume_text.get('mobile number')
                resume_text['email'] = resume_text.get('id') or resume_text.get('email') or resume_text.get('email id')
                # resume_text['skills']=resume_text.get('languages') or resume_text.get('database') or resume_text.get('skills') or resume_text.get('others')
                if 'languages' in resume_text:
                    resume_text['skills']=resume_text['skills']+","+resume_text['languages']
                    resume_text['languages']='N/A' 
                if 'database' in resume_text:
                    resume_text['skills']=resume_text['skills']+","+resume_text['database']
                    resume_text['database']='N/A'
                if 'others' in resume_text:
                    resume_text['skills']=resume_text['skills']+","+resume_text['others']
                    resume_text['others']='N/A'

                     
                keys_to_remove = [k for k, v in resume_text.items() if v == 'N/A' or v=='NULL']
                for k in keys_to_remove:
                    del resume_text[k]
                
                msg=""
                course=""
                msgdis=""
                # resume_data=str(resume_text)
                ds_keyword = ['tensorflow','keras','pytorch','machine learning','deep learning','flask','streamlit','machine learning','artificial intelligence','ai/ml']
                web_keyword = ['react', 'django', 'node js', 'react js', 'php', 'laravel', 'magento', 'wordpress','javascript', 'angular js', 'c#', 'asp.net', 'flask']
                android_keyword = ['android','android development','flutter','kotlin','xml','kivy']
                ios_keyword = ['ios','ios development','swift','cocoa','cocoa touch','xcode']
                uiux_keyword = ['ux','adobe xd','figma','zeplin','balsamiq','ui','prototyping','wireframes','storyframes','adobe photoshop','photoshop','editing','adobe illustrator','illustrator','adobe after effects','after effects','adobe premier pro','premier pro','adobe indesign','indesign','wireframe','solid','grasp','user research','user experience']
                n_any = ['english','communication','writing', 'microsoft office', 'leadership','customer management', 'social media']
                    ### Skill Recommendations Starts                
                recommended_skills = []
                reco_field = ''
                rec_course = ''
                
                
                    ### condition starts to check skills from keywords and predict field
                for i in re.split(r',|-', resume_text['skills']):
                    a=str(i.lower())
                    a=a.strip()
                    
                    #### Data science recommendation
                    if a in ds_keyword:
                        st.write(i.lower())
                        
                        reco_field = 'Data Science'
                        msg="Our analysis says you are looking for Data Science Jobs."
                        recommended_skills = ['Data Visualization','Predictive Analysis','Statistical Modeling','Data Mining','Clustering & Classification','Data Analytics','Quantitative Analysis','Web Scraping','ML Algorithms','Keras','Pytorch','Probability','Scikit-learn','Tensorflow',"Flask",'Streamlit']
                                                   
                        # st.markdown('''<h5 style='text-align: left; color: #1ed760;'>These skills will help you in your Carrier building</h5>''',unsafe_allow_html=True)
                        # course recommendation
                        course=ds_course
                        
                        break

                        #### Web development recommendation
                    elif a in web_keyword:
                            print(i.lower())
                            reco_field = 'Web Development'
                            msg="Our analysis says you are looking for Web Development Jobs"
                            recommended_skills = ['React','Django','Node JS','React JS','php','laravel','Magento','wordpress','Javascript','Angular JS','c#','Flask','SDK']
                            msgdis=f'''<h5 style='text-align: left; color: grey;'>These skills will help you in your Carrier building</h5>'''
                            
                            # course recommendation
                            course=web_course
                            
                            break

                        #### Android App Development
                    elif a in android_keyword:
                            print(i.lower())
                            reco_field = 'Android Development'
                            msg="Our analysis says you are looking for Android App Development Jobs"

                            recommended_skills = ['Android','Android development','Flutter','Kotlin','XML','Java','Kivy','GIT','SDK','SQLite']
                            msgdis=f'''<h5 style='text-align: left; color: grey;'>These skills will help you in your Carrier building</h5>'''
                            # course recommendation
                            course=android_course
                            break

                        #### IOS App Development
                    elif a in ios_keyword:
                            print(i.lower())
                            reco_field = 'IOS Development'
                            msg="Our analysis says you are looking for IOS App Development Jobs"
                            
                            recommended_skills = ['IOS','IOS Development','Swift','Cocoa','Cocoa Touch','Xcode','Objective-C','SQLite','Plist','StoreKit',"UI-Kit",'AV Foundation','Auto-Layout']
                            msgdis=f'''<h5 style='text-align: left; color: grey;'>These skills will help you in your Carrier building</h5>'''
                            # course recommendation
                            course=ios_course
                            break

                        #### Ui-UX Recommendation
                    elif a in uiux_keyword:
                            print(i.lower())
                            reco_field = 'UI-UX Development'
                            msg="Our analysis says you are looking for UI-UX Development Jobs"
                            recommended_skills = ['UI','User Experience','Adobe XD','Figma','Zeplin','Balsamiq','Prototyping','Wireframes','Storyframes','Adobe Photoshop','Editing','Illustrator','After Effects','Premier Pro','Indesign','Wireframe','Solid','Grasp','User Research']
                            msgdis=f'''<h5 style='text-align: left; color: grey;'>These skills will help you in your Carrier building</h5>'''
                            # course recommendation
                            course=uiux_course
                            break

                        #### For Not Any Recommendations
                    elif a in n_any:
                            print(i.lower())
                            reco_field = 'NA'
                            msg="Currently our tool only predicts and recommends for Data Science, Web, Android, IOS and UI/UX Development"
                            recommended_skills = ['No Recommendations']
                            
                            msgdis=f'''<h5 style='text-align: left; color:grey;'>Maybe Available in Future Updates</h5>'''
                            # course recommendation
                            course="Sorry! Not Available for this Field"
                            break
                    else:
                            pass
                
                    
                
                if 'experience' in resume_text:
                        cand_level = "Experienced"
                        candi=f'''<h4 style='text-align: left; color: #fba171;'>You are at experience level!'''
                elif 'intern' in resume_text:
                        cand_level = "Intermediate"
                        candi=f'''<h4 style='text-align: left; color: #1ed760;'>You are at intermediate level!</h4>'''
                else:
                        cand_level = "Fresher"
                        candi=f'''<h4 style='text-align: left; color: #fba171;'>You are at Fresher level!!'''
                
                resume_score = 0
                if 'Objective' or 'Summary' in resume_text:
                        resume_score = resume_score+6
                        omsg=f'''<h5 style='text-align: left; color: grey;'>[+] Awesome! You have added Objective/Summary</h4>'''               
                else:
                        omsg=f'''<h5 style='text-align: left; color: yellow;'>[-] Please add your career objective, it will give your career intension to the Recruiters.</h4>'''

                if 'Education' or 'School' or 'College'  in resume_text:
                        resume_score = resume_score + 12
                        umsg=f'''<h5 style='text-align: left; color: grey;'>[+] Awesome! You have added Education Details</h4>'''
                else:
                        umsg=f'''<h5 style='text-align: left; color: yellow;'>[-] Please add Education. It will give Your Qualification level to the recruiter</h4>'''

                if 'experience' in resume_text:
                        resume_score = resume_score + 16
                        emsg='''<h5 style='text-align: left; color: grey;'>[+] Awesome! You have added Experience</h4>'''
                else:
                        emsg=f'''<h5 style='text-align: left; color: yellow;'>[-] Please add Experience. It will help you to stand out from crowd</h4>'''                    
                if 'intern' in resume_text:
                        resume_score = resume_score + 6
                        imsg=f'''<h5 style='text-align: left; color: grey;'>[+] Awesome! You have added Internships</h4>'''
                else:
                        imsg=f'''<h5 style='text-align: left; color: yellow;'>[-] Please add Internships. It will help you to stand out from crowd</h4>'''

                if 'SKILLS' or 'skills' or 'skill' or 'SKILL' or 'Skills' or 'Skill'  in resume_text:
                        resume_score = resume_score + 7
                        smsg=f'''<h5 style='text-align: left; color: grey;'>[+] Awesome! You have added Skills</h4>'''
                else:
                        smsg=f'''<h5 style='text-align: left; color: yellow;'>[-] Please add Skills. It will help you a lot</h4>'''

                if 'HOBBIES'  or 'hobbies' or  'Hobbies' or 'hobbie'  in resume_text:
                        resume_score = resume_score + 4
                        hmsg=f'''<h5 style='text-align: left; color: grey;'>[+] Awesome! You have added your Hobbies</h4>'''
                else:
                        hmsg=f'''<h5 style='text-align: left; color: yellow;'>[-] Please add Hobbies. It will show your personality to the Recruiters and give the assurance that you are fit for this role or not.</h4>'''
                    
                if 'INTERESTS' or 'interest' or 'Interests'  in resume_text:
                        resume_score = resume_score + 5
                        
                        inmsg=f'''<h5 style='text-align: left; color: grey;'>[+] Awesome! You have added your Interest</h4>'''
                else:
                        inmsg=f'''<h5 style='text-align: left; color: yellow;'>[-] Please add Interest. It will show your interest other that job.</h4>'''

                if 'ACHIEVEMENTS' or 'Achievements' or 'achievements' in resume_text:
                        resume_score = resume_score + 13
                        amsg=f'''<h5 style='text-align: left; color: grey;'>[+] Awesome! You have added your Achievements </h4>'''
                else:
                        amsg=f'''<h5 style='text-align: left; color: yellow;'>[-] Please add Achievements. It will show that you are capable for the required position.</h4>'''

                if 'CERTIFICATIONS' or 'certification' or 'certifications' or 'Certifications' or 'Certification' in resume_text:
                        resume_score = resume_score + 12
                        cmsg=f'''<h5 style='text-align: left; color: grey;'>[+] Awesome! You have added your Certifications </h4>'''
                else:
                        cmsg=f'''<h5 style='text-align: left; color: yellow;'>[-] Please add Certifications. It will show that you have done some specialization for the required position.</h4>'''

                if 'PROJECTS' or 'PROJECT' or 'Projects' or 'projects' or 'Project' in resume_text:
                        resume_score = resume_score + 19
                        pmsg=f'''<h5 style='text-align: left; color: grey;'>[+] Awesome! You have added your Projects</h4>'''
                else:
                        pmsg=f'''<h5 style='text-align: left; color: yellow;'>[-] Please add Projects. It will show that you have done work related the required position or not.</h4>'''

                ts = time.time()
                cur_date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                cur_time = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                timestamp = str(cur_date+'_'+cur_time)
                
                resume_text['email'] = resume_text.get('id') or resume_text.get('email') or resume_text.get('email id')
                
                ## Calling insert_data to add all the data into user_data                
                resume_text['skills']=resume_text['skills'].lower()
                insert_data(str(sec_token), str(ip_add), (host_name), (dev_user), (os_name_ver), (latlong), (act_city), (act_state), (country), (act_name), (act_mail), (act_mob), resume_text['name'], resume_text['email'], str(resume_score), timestamp,"N/A", reco_field, cand_level, str(resume_text['skills']), str(recommended_skills), str(rec_course),pdf_name)
                



                option = st.multiselect('Choose one or more', ['Resume Details', 'Course Recommendations', 'Resume Scoring'])
            
                if 'Resume Details' in option:
                    st.success("Hello "+ resume_text['name'])
                    st.subheader(" Your Basic info  ")
                    try:
                        # st.text('Name: ' + resume_text['name'])
                        # st.text('Email: ' + resume_text['email'])
                        # st.text('Contact: ' + resume_text['number'])
                        # st.text('Degree: '+resume_text['degree'])  
                        st.write(resume_data)                  
                        
                    except:
                        pass
           
                    
                    
                

                if 'Course Recommendations' in option:
                    st.subheader("Skills")
                    st.write(resume_text['skills'])
                    st.write(msg)
                    recommended_keywords =  st_tags(label='### Recommended skills for you.',
                    text='Recommended skills generated from System',value=recommended_skills,key = '2')
                    if course!="Sorry! Not Available for this Field":
                        rec_course = course_recommender(course)
                    else:
                        st.write("Sorry! Not Available for this Field")
                    st.markdown({msgdis},unsafe_allow_html=True)
                    st.write(rec_course)
                    ## Resume Scorer & Resume Writing Tips
                    
                    st.header("Bonus Video for Resume Writing Tips")
                    resume_vid = random.choice(resume_videos)
                
                    st.video(resume_vid)

                    ## Recommending Interview Preparation Video
                    st.header(" Bonus Video for Interview Tips ")
                    interview_vid = random.choice(interview_videos)
                    st.video(interview_vid)
                    
                    
                if 'Resume Scoring' in option:
                    
                    st.markdown(candi,unsafe_allow_html=True)
                    st.subheader("Resume Tips & Ideas")
                    st.markdown(omsg,unsafe_allow_html=True)
                    st.markdown(umsg,unsafe_allow_html=True)
                    st.markdown(emsg,unsafe_allow_html=True)
                    st.markdown(imsg,unsafe_allow_html=True)
                    st.markdown(smsg,unsafe_allow_html=True)
                    st.markdown(hmsg,unsafe_allow_html=True)
                    st.markdown(inmsg,unsafe_allow_html=True)
                    st.markdown(amsg,unsafe_allow_html=True)
                    st.markdown(cmsg,unsafe_allow_html=True)
                    st.markdown(pmsg,unsafe_allow_html=True)
                    ### Predicting Whether these key points are added to the resume
                    
                    st.subheader("Resume Score")
                    
                    st.markdown(
                        """
                        <style>
                            .stProgress > div > div > div > div {
                                background-color: #d73b5c;
                            }
                        </style>""",
                        unsafe_allow_html=True,
                    )

                    ### Score Bar
                    my_bar = st.progress(0)
                    score = 0
                    for percent_complete in range(resume_score):
                        score +=1
                        time.sleep(0.1)
                        my_bar.progress(percent_complete + 1)

                    ### Score
                    st.success('  Your Resume Writing Score: ' + str(score)+' ')
                    st.warning("  Note: This score is calculated based on the content that you have in your Resume.  ")

                # print(str(sec_token), str(ip_add), (host_name), (dev_user), (os_name_ver), (latlong), (city), (state), (country), (act_name), (act_mail), (act_mob), resume_data['name'], resume_data['email'], str(resume_score), timestamp, str(resume_data['no_of_pages']), reco_field, cand_level, str(resume_data['skills']), str(recommended_skills), str(rec_course), pdf_name)


                ### Getting Current Date and Time
                
                
                
                
                
                
                # SQL Query to fetch data
                # query = '''
                # SELECT ID
                # FROM user_data 
                # WHERE act_name=%s AND act_mob=%s
                # '''
                # cursor.execute(query, (act_name, act_mob))
                # data = cursor.fetchall()

                # # Convert the result to a string for the email body
                # if data:
                #     unique_id = data[0][0]
                #     body = f"Your Unique ID is: {unique_id}. Thank you for submitting your resume."
                # else:
                #     body = "We could not find your submission. Please try again."

                # # Send the email and show success message in Streamlit
                # if send_email("Resume Submission", body, act_mail) == "Email sent successfully!":
                #     st.success(body)
                # else:
                #     st.error("Failed to send email.")
                # ## Recommending Resume Writing Video
                

                




                

                

            else:
                st.error("Something went wrong..")                

            
    ###### CODE FOR FEEDBACK SIDE ######
    elif choice == 'Feedback':   
        
        # timestamp 
        ts = time.time()
        cur_date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
        cur_time = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
        timestamp = str(cur_date+'_'+cur_time)

        # Feedback Form
        with st.form("my_form"):
            st.write("Feedback form")            
            feed_name = st.text_input('Name')
            feed_email = st.text_input('Email')
            feed_score = st.slider('Rate Us From 1 - 5', 1, 5)
            comments = st.text_input('Comments')
            Timestamp = timestamp        
            submitted = st.form_submit_button("Submit")
            if submitted:
                ## Calling insertf_data to add dat into user feedback
                insertf_data(feed_name,feed_email,feed_score,comments,Timestamp)    
                ## Success Message 
                st.markdown("Thanks! Your Feedback was recorded.")     


        # query to fetch data from user feedback table
        query = 'select * from user_feedback'        
        plotfeed_data = pd.read_sql(query, connection)                        


        # fetching feed_score from the query and getting the unique values and total value count 
        labels = plotfeed_data.feed_score.unique()
        values = plotfeed_data.feed_score.value_counts()


        # plotting pie chart for user ratings
        st.subheader(" Past User Rating's ")
        fig = px.pie(values=values, names=labels, title="User Rating Analysis", color_discrete_sequence=px.colors.sequential.Aggrnyl)
        st.plotly_chart(fig)


        #  Fetching Comment History
        cursor.execute('select feed_name, comments from user_feedback')
        plfeed_cmt_data = cursor.fetchall()

        st.subheader(" User Comment's ")
        dff = pd.DataFrame(plfeed_cmt_data, columns=['User', 'Comment'])
        st.dataframe(dff, width=1000)

    
    ###### CODE FOR ABOUT PAGE ######
    elif choice == 'About':   

        st.subheader(" About The Tool - AI RESUME ANALYZER ")

        st.markdown('''

        <p align='justify'>
            A tool which parses information from a resume using natural language processing and finds the keywords, cluster them onto sectors based on their keywords. And lastly show recommendations, predictions, analytics to the applicant based on keyword matching.
        </p>

        <p align="justify">
            <b>How to use it: -</b> <br/><br/>
            <b>User -</b> <br/>
            In the Side Bar choose yourself as user and fill the required fields and upload your resume in pdf format.<br/>
            Just sit back and relax our tool will do the magic on it's own.<br/><br/>
            <b>Feedback -</b> <br/>
            A place where user can suggest some feedback about the tool.<br/><br/>
            <b>Admin -</b> <br/>
            For login use <b>admin</b> as username and <b>admin</b> as password.<br/>
            It will load all the required stuffs and perform analysis.
        </p><br/><br/>

        <p align="justify">
            Built with  by 
            <a href="" style="text-decoration: none; color: grey;"> Ernst & Young</a> 
            <a href="" style="text-decoration: none; color: grey;"></a>
        </p>

        ''',unsafe_allow_html=True)  


    ###### CODE FOR ADMIN SIDE (ADMIN) ######
    else:
        st.markdown('Welcome to Admin Side! ')
        if 'ad_skill' not in st.session_state:
            st.session_state.ad_skill = ''
        #  Admin Login
        ad_user = st.text_input("Username")
        
        ad_password = st.text_input("Password", type='password')
        ad_skill=st.text_input("Skills to be searched")
        ad_skill=ad_skill.lower()
        if st.button('Login'):
           
            
            ## Credentials 
            if ad_user == 'admin' and ad_password == 'admin':
                ### Fetch miscellaneous data from user_data(table) and convert it into dataframe
               
                

                cursor.execute('''SELECT ID, ip_add, resume_score, convert(Predicted_Field using utf8), convert(User_level using utf8), city, state, country from user_data''')
                datanalys = cursor.fetchall()
                plot_data = pd.DataFrame(datanalys, columns=['ID', 'IP_add', 'resume_score', 'Predicted_Field', 'User_Level', 'City', 'State', 'Country'])
                
                ### Total Users Count with a Welcome Message
                values = len(plot_data)
               
                st.markdown("Welcome! Total %d " % values + " User's Have Used Our Tool")                
                # ad_skill=st.text_input("Skills to be searched")
                # st.text(ad_skill)
                if ad_skill:

                    ad_skilld=split_text_to_list(ad_skill)
                    where_clause = " AND ".join([f"Actual_skills LIKE '%{skill}%'" for skill in ad_skilld])

                        
                        ### Fetch user data from user_data(table) and convert it into dataframe
                    query = f'''
                        SELECT ID, sec_token, ip_add, act_name, act_mail, act_mob, convert(Predicted_Field using utf8), Timestamp, 
                            Name, Email_ID, resume_score, Page_no, pdf_name, convert(User_level using utf8), 
                            convert(Actual_skills using utf8), convert(Recommended_skills using utf8), 
                            convert(Recommended_courses using utf8), city, state, country, latlong, 
                            os_name_ver, host_name, dev_user 
                        FROM user_data 
                        WHERE {where_clause} order by resume_score DESC
    '''
                    cursor.execute(query)
                    data = cursor.fetchall()
                    # Create dataframe for user data
                    user_columns = ['ID', 'Token', 'IP Address', 'Actual Name', 'Actual Mail', 'Actual Mobile', 'Predicted Field', 'Timestamp',
                                        'Name', 'Email_ID', 'Resume Score', 'Page Number', 'PDF Name', 'User Level', 'Actual Skills', 
                                        'Recommended Skills', 'Recommended Courses', 'City', 'State', 'Country', 'Lat Long', 'Server OS', 
                                        'Host Name', 'Server User']
                    df = pd.DataFrame(data, columns=user_columns)
                else:
                    query = f'''
                        SELECT ID, sec_token, ip_add, act_name, act_mail, act_mob, convert(Predicted_Field using utf8), Timestamp, 
                            Name, Email_ID, resume_score, Page_no, pdf_name, convert(User_level using utf8), 
                            convert(Actual_skills using utf8), convert(Recommended_skills using utf8), 
                            convert(Recommended_courses using utf8), city, state, country, latlong, 
                            os_name_ver, host_name, dev_user 
                        FROM user_data 
                        order by resume_score DESC
    '''
                    cursor.execute(query)
                    data = cursor.fetchall()
                    # Create dataframe for user data
                    user_columns = ['ID', 'Token', 'IP Address', 'Actual Name', 'Actual Mail', 'Actual Mobile', 'Predicted Field', 'Timestamp',
                                        'Name', 'Email_ID', 'Resume Score', 'Page Number', 'PDF Name', 'User Level', 'Actual Skills', 
                                        'Recommended Skills', 'Recommended Courses', 'City', 'State', 'Country', 'Lat Long', 'Server OS', 
                                        'Host Name', 'Server User']
                    df = pd.DataFrame(data, columns=user_columns)


                    # Display user data
                st.header(" User's Data ")
                st.dataframe(df)
                    # Download link for user data
                st.markdown(get_csv_download_link(df, 'User_Data.csv', 'Download Report'), unsafe_allow_html=True)

                        # Fetch feedback data
                cursor.execute('''SELECT * FROM user_feedback''')
                feedback_data = cursor.fetchall()

                        # Create dataframe for feedback data                    
                feedback_columns = ['ID', 'Name', 'Email', 'Feedback Score', 'Comments', 'Timestamp']
                df_feedback = pd.DataFrame(feedback_data, columns=feedback_columns)

                        # Display feedback data
                st.header(" User's Feedback Data ")
                st.dataframe(df_feedback)

                        # Fetching feedback data for plotting
                query = 'SELECT * FROM user_feedback'
                plotfeed_data = pd.read_sql(query, connection)

                        # Analyzing all the data in pie charts

                        # User ratings pie chart
                labels = plotfeed_data['feed_score'].unique()
                values = plotfeed_data['feed_score'].value_counts()

                    # Ensure values and labels are converted to lists for plotting
                labels = labels.tolist()
                values = values.tolist()

                        
                fig = px.pie(values=values, names=labels, title="User Rating Analysis", color_discrete_sequence=px.colors.sequential.Aggrnyl)
                st.plotly_chart(fig)

                        # Predicted field recommendations pie chart
                labels = df['Predicted Field'].unique()
                values = df['Predicted Field'].value_counts()

                        # Ensure values and labels are converted to lists for plotting
                labels = labels.tolist()
                values = values.tolist()

                fig = px.pie(values=values, names=labels, title='Predicted Field according to the Skills ', color_discrete_sequence=px.colors.sequential.Aggrnyl_r)
                st.plotly_chart(fig)

                        # User levels pie chart
                labels = df['User Level'].unique()
                values = df['User Level'].value_counts()

                        # Ensure values and labels are converted to lists for plotting
                labels = labels.tolist()
                values = values.tolist()

                fig = px.pie(values=values, names=labels, title='Users Experience Levels ', color_discrete_sequence=px.colors.sequential.Aggrnyl_r)
                st.plotly_chart(fig)

                        # fetching IP_add from the query and getting the unique values and total value count 
                labels = df['IP Address'].unique()
                values = df['IP Address'].value_counts()

                        # Pie chart for Users
                fig = px.pie(values=values, names=labels, title='Users Access based on IP Address', color_discrete_sequence=px.colors.sequential.matter)
                st.plotly_chart(fig)

                        # fetching City from the query and getting the unique values and total value count 
                labels = df['City'].unique()
                values = df['City'].value_counts()

                        # Pie chart for City
                fig = px.pie(values=values, names=labels, title='Users access based On City ', color_discrete_sequence=px.colors.sequential.Jet)
                st.plotly_chart(fig)

                        # fetching State from the query and getting the unique values and total value count 
                labels = df['State'].unique()
                values = df['State'].value_counts()
                        
                        # Pie chart for State
                fig = px.pie(values=values, names=labels, title='Users access based On State ', color_discrete_sequence=px.colors.sequential.PuBu)
                st.plotly_chart(fig)

                        # fetching Country from the query and getting the unique values and total value count 
                labels = df['Country'].unique()
                values = df['Country'].value_counts()

                fig = px.pie(values=values, names=labels, title='Users access based On Country ', color_discrete_sequence=px.colors.sequential.Purp)
                st.plotly_chart(fig)
                

            ## For Wrong Credentials
            else:
                st.error("Wrong ID & Password Provided")

# Calling the main (run()) function to make the whole process run
if __name__ == "__main__":
    run()
