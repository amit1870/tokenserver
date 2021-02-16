import json
import uuid
import random
import threading
from time import time
from flask import Flask, abort, jsonify
from flask_restful import Resource, Api, reqparse

app = Flask(__name__)
api = Api(app)
parser = reqparse.RequestParser()
parser.add_argument('token')

token_pool = []
blocked_tokens = []


class Token:
    def __init__(self, token_id):
        self.id = token_id
        
    def get_id(self):
        return self.id

    def get_refreshed_time(self):
        return self.refreshed_time

    def update_generated_time(self, time_stamp=None):
        self.generated_time = time() if time_stamp is None else time_stamp

    def update_refresh_time(self, time_stamp=None):
        self.refreshed_time = time() if time_stamp is None else time_stamp

class TokenGenerator(Resource):
    def get(self):
        global token_pool
        token_pool = [Token(str(uuid.uuid4())) for i in range(5)]
        token_obj_str = []
        for token_obj in token_pool:
            token_obj.update_generated_time()
            token_obj.update_refresh_time()
            token_obj_str.append(token_obj.get_id())
        return token_obj_str
        

class AssignToken(Resource):
    def get(self):
        global token_pool, blocked_tokens
        if len(token_pool):
            index = random.randint(0,len(token_pool)-1)
            assigned_token = token_pool[index]
            token_pool.remove(assigned_token)
            blocked_tokens.append(assigned_token)
        else:
            return abort(404)
        return assigned_token.get_id()

class FreeToken(Resource):
    def delete(self, token):
        global token_pool, blocked_tokens
        for blocked_token in blocked_tokens:
            if blocked_token.get_id() == token:
                token_pool.append(blocked_token)
                blocked_tokens.remove(blocked_token)
                return '', 204
        else:
            return abort(404)


class DeleteToken(Resource):
    def delete(self, token):
        global token_pool
        for free_token in token_pool:
            if free_token.get_id() == token:
                token_pool.remove(free_token)
                return '', 204
        else:
            return abort(404)

class KeepAlive(Resource):
    def put(self, token):
        global token_pool
        for free_token in token_pool:
            if free_token.get_id() == token:
                refreshed_time = free_token.get_refreshed_time()
                if refreshed_time - time() > 300:
                    token_pool.remove(free_token)
                else:
                    free_token.update_refresh_time(time())
                return free_token.get_id()
        else:
            return abort(404)


@app.before_first_request
def free_blocked_token_after_60s():
    def run_job():
        while True:
            global blocked_tokens
            expired_tokens = []
            for token in blocked_tokens:
                if time() - token.get_refreshed_time() > 60:
                    expired_tokens.append(token)

            for token in expired_tokens:
                blocked_tokens.remove(token)
                token.update_refresh_time(time())
                token_pool.append(token)
    thread = threading.Thread(target=run_job)
    thread.start()

api.add_resource(TokenGenerator, '/generate-token')
api.add_resource(AssignToken, '/assign-token')
api.add_resource(FreeToken, '/free-token/<token>')
api.add_resource(DeleteToken, '/delete-token/<token>')
api.add_resource(KeepAlive, '/keep-alive/<token>')

if __name__ == '__main__':
    app.run(debug=True)
