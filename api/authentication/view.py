# -*- coding: utf-8 -*-
from flask_restful import Resource, reqparse, request
from flask import flash, redirect, Blueprint, current_app
from flask_security import login_required, login_user, logout_user
from .model import User, Permission, Groups
from utils.permission import permisson_required, sso_required
from utils.ext import db
from flask_login import current_user
import json
import logging
from utils.ErrorCode import *
import jwt
from flask_jwt import jwt_required, current_identity


module = Blueprint('logout', __name__)


@module.route('/logout')
def logout():
    logout_user()
    return "logout ok"


class Auth(Resource):
    def __init__(self):
        super(Auth, self).__init__()

    @sso_required
    @login_required
    def get(self):
        """
        sso单点登录
        ---
        tags:
        - AUTH
        parameters:
          - in: body
            name: ticket
            type: string
            required: true
          - in: body
            name: service
            type: string
            required: true
        responses:
          200:
            description: sso认证登录
            schema:
              properties:
                result:
                  type: string
                  default: ok
            examples:
                {
                    "result": {
                        "exp": 1498621139,
                        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI",
                        "username": "lifei5"
                    },
                    "state": "ok"
                }
        """
        username = None
        token = None
        exp = None
        state = STATE_OK
        try:
            username = current_user.username
            password = current_app.config.get('PASSWORD_KEY')
            _secret = current_app.config.get('SECRET_KEY')

            with current_app.test_client() as c:
                resp = c.post('/auth', headers={'Content-Type': 'application/json'},
                              data=json.dumps({"username": username, "password": password}))
                data = json.loads(resp.data.decode('utf8'))

            token = data.get('access_token', None)
            exp = jwt.decode(token, key=_secret).get("exp")

        except Exception as e:
            logging.error("get token error: %s." % str(e))
            state = isinstance(e, ErrorCode) and e or ErrorCode(1, "unknown error:" + str(e))

        return {'result': {'username': username, 'token': token, 'exp': exp}, 'state': state.message}, state.eid


class Users(Resource):
    def __init__(self):
        self.parser = reqparse.RequestParser()
        self.parser.add_argument('user', type=str, required=True, location='form')
        self.parser.add_argument('passwd', type=str, required=True, location='form')

        self.parser_get = reqparse.RequestParser()
        self.parser_get.add_argument('user', type=str, required=False, location='args')
        super(Users, self).__init__()

    @jwt_required()
    def get(self):
        """
            员工信息查询接口
            ---
            tags:
            - USER
            parameters:
              - in: header
                name: Authorization
                type: string
                required: true
                description: "JWT <token>"
            responses:
              200:
                description: 员工信息查询接口
        """
        doc = {}
        state = STATE_OK

        try:
            doc = current_identity.__dict__
            del doc['password_hash']
            del doc['_sa_instance_state']
            del doc['confirmed_at']

        except Exception as e:
            logging.error("get user info error: %s." % str(e))
            state = isinstance(e, ErrorCode) and e or ErrorCode(1, "unknown error:" + str(e))

        return {'result': doc, 'state': state.message}, state.eid

    @jwt_required()
    def post(self):
        """
            员工信息修改接口
            ---
            tags:
            - USER
            parameters:
              - in: header
                name: Authorization
                type: string
                required: true
                description: "JWT <token>"
              - in: formData
                name: phone
                type: string
                description: "手机"
              - in: formData
                name: email
                type: string
                description: "邮箱"
            responses:
              200:
                description: 员工信息修改接口
        """

        state = STATE_OK
        rs = False
        try:
            uid = current_identity.__dict__.get('id')
            phone = request.values.get("phone", None)
            email = request.values.get("email", None)
            user = User.query.get(int(uid))
            if phone or email:
                if phone:
                    user.phone = phone

                if email:
                    user.email = email

                db.session.add(user)
                db.session.commit()

                rs = True

            else:
                raise STATE_PARAM_ERR

        except Exception as e:
            logging.error("get user info error: %s." % str(e))
            state = isinstance(e, ErrorCode) and e or ErrorCode(1, "unknown error:" + str(e))

        return {'result': rs, 'state': state.message}, state.eid


class UserQuery(Resource):
    def __init__(self):
        super(UserQuery, self).__init__()

    def get(self, nt_account):
        """
            指定账户员工信息查询接口
            ---
            tags:
            - USER
            parameters:
              - in: path
                name: nt_account
                type: string
                required: true
                description: "nt_account "
            responses:
              200:
                description: 指定员工信息查询接口
        """
        doc = {}
        state = STATE_OK

        try:
            user = User.query.filter_by(username=nt_account).first()
            if not user:
                raise STATE_EmptyData_ERR

            doc.update({'email': user.email, 'phone': user.phone})

        except Exception as e:
            logging.error("get user info error: %s." % str(e))
            state = isinstance(e, ErrorCode) and e or ErrorCode(1, "unknown error:" + str(e))

        return {'result': doc, 'state': state.message}, state.eid



