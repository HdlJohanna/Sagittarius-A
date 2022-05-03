import contextlib
from io import StringIO
import os
import shutil
import subprocess
import traceback
import requests
import sys
import logging
from flask import Flask, request
from github import Github, GithubIntegration
import toml
import configparser

app = Flask("saga")

app_id = 196288


with open(os.path.normpath(os.path.expanduser('~/.certs/github/sagittarius-a-key.pem')),'r') as certfile:
    app_key = certfile.read()

git_integration = GithubIntegration(app_id,app_key)

@app.route("/",methods=["POST"])
def root():
    
    stdout = StringIO()
    logging.basicConfig(level=logging.DEBUG,stream=stdout)
    logger = logging.getLogger(__name__)
    Parser = configparser.ConfigParser()
    with open("channel.conf"):
        payload = request.json

        owner = payload['repository']['owner']['login']
        repo_name = payload['repository']['name']

        git = Github(
            git_integration.get_access_token(
                git_integration.get_installation(owner, repo_name).id
            ).token
        )

        repo = git.get_repo(f'{owner}/{repo_name}')
        try:
            try:
                sagittarius_data = repo.get_contents("sagittarius-depl.cfg")
                if not sagittarius_data:
                    return 'ok'
            except:
                return 'ok'
            print("here")
            print(sagittarius_data.decoded_content.decode('utf8'))
            contents = Parser.read_string(sagittarius_data.decoded_content.decode('utf8'))
            image = Parser.get("DOCKER","image")
            entrypoint = Parser.get("DOCKER","image")
            if os.path.exists(owner):
                shutil.rmtree(owner)
            os.system(f'git clone {repo.clone_url} {owner}')
            entr = entrypoint.split(' ')
            with open(owner+"/dockerfile", "w") as f:
                f.write(
                    f"""
    FROM {image}
    COPY * .
    CMD {entr}
                    """
                )

            io = subprocess.Popen(["docker","rm", "-f", repo_name],stdout=subprocess.PIPE).communicate()[0].decode()
            io = subprocess.Popen(["docker", "build", "-t", repo_name, owner],stdout=subprocess.PIPE).communicate()[0].decode()
            repo.create_issue("Deployment Status",f"Displaying Results of last Deployment: ```sh\n{io}```")
            failed = False
            error = None
        except Exception as _error:
            failed = True
            error = _error
            
            logger.exception(_error)

    if failed:
        repo.create_issue("Deployment failed",f"The Deployment and Dockerization of your app failed.\n```py\n{error.__class__.__name__}\n{error.args}\n{error.__doc__}\n```\nThis is most likely not a Problem with Sagittarius.\nPlease make sure that\n* Your sagittari.toml File is present and working\n* Your `entry-point` is a working command")
        return 'ok'

@app.route("/addrepo")
def ar():
    print("ping")
    payload = request.json

    owner = payload['repo']['login']
    repo_name = payload['repo']['name']

    git = Github(
        git_integration.get_access_token(
            git_integration.get_installation(owner, repo_name).id
        ).token
    )

    Parser = configparser.ConfigParser()

    repo = git.get_repo(f'{owner}/{repo_name}')
    try:
        try:
            sagittarius_data = repo.get_contents("sagittarius-depl.cfg")
            if not sagittarius_data:
                
                sagittarius_data = repo.create_file("sagittarius-depl.cfg",'Create Deployment File',
            '''
[DOCKER]
image = ubuntu:16.04
entry-point = ls
            ''')
        except:
                sagittarius_data = repo.create_file("sagittarius-depl.cfg",'Create Deployment File',
                '''
[DOCKER]
image = ubuntu:16.04
entry-point = ls
            ''')
        print("here")
        print(sagittarius_data.content)
        contents = Parser.read_string(sagittarius_data.content)
        image = contents["DOCKER"]["image"]
        entrypoint = contents["DOCKER"]["entry-point"]
        os.system(f'git clone {repo.clone_url} {owner}')
        entr = entrypoint.split(' ')
        with open(owner+"/dockerfile", "w") as f:
            f.write(
                f"""
FROM {image}
COPY * .
CMD {entr}
                """
            )
        io = subprocess.Popen(["docker","rm", "-f", repo],stdout=subprocess.PIPE).communicate()[0].decode()
        io = subprocess.Popen(["docker", "build", "-t", repo, owner],stdout=subprocess.PIPE).communicate()[0].decode()
        repo.create_issue("Deployment Status",f"Displaying Results of last Deployment: ```sh\n{io}```")
        failed = False
        error = None
    except Exception as _error:
        failed = True
        error = _error
        
    if failed:
        repo.create_issue("Deployment failed",f"The Deployment and Dockerization of your app failed.\n```py\n{error.__class__.__name__}\n{error.args}\n{error.__doc__}\n```\nThis is most likely not a Problem with Sagittarius.\nPlease make sure that\n* Your sagittari.toml File is present and working\n* Your `entry-point` is a working command")
        return 'ok'



app.run(debug=True)
