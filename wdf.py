#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import urllib, urllib2
import re
import cookielib
import time
import xml.dom.minidom
import json
import sys
import math
import tornado


DEBUG = False

MAX_GROUP_NUM = 35  # 每组人数

QRImagePath = os.getcwd() + '/qrcode.jpg'

tip = 0
uuid = ''

base_uri = ''
redirect_uri = ''

skey = ''
wxsid = ''
wxuin = ''
pass_ticket = ''
deviceId = 'e000000000000000'

BaseRequest = {}

ContactList = []
My = []
loginfo = []


def getUUID():
  try:
    global uuid

    url = 'https://login.weixin.qq.com/jslogin'
    params = {
    'appid': 'wx782c26e4c19acffb',
    'fun': 'new',
    'lang': 'zh_CN',
    '_': int(time.time()),
    }

    request = urllib2.Request(url=url, data=urllib.urlencode(params))
    response = urllib2.urlopen(request)
    data = response.read()

    # print data

    # window.QRLogin.code = 200; window.QRLogin.uuid = "oZwt_bFfRg==";
    regx = r'window.QRLogin.code = (\d+); window.QRLogin.uuid = "(\S+?)"'
    pm = re.search(regx, data)

    code = pm.group(1)
    uuid = pm.group(2)

    if code == '200':
      return True

    return False
  except Exception:
    return False

def loggedRequest():
  try:
    if webwxinit() == False:
      print '初始化失败'
      loginfo.append('初始化失败')
    else:
      MemberList = webwxgetcontact()

      MemberCount = len(MemberList)
      print '通讯录共%s位好友' % MemberCount
      loginfo.append('通讯录共%s位好友' % MemberCount)

      ChatRoomName = ''
      result = []
      for i in xrange(0, int(math.ceil(MemberCount / float(MAX_GROUP_NUM)))):
        UserNames = []
        NickNames = []
        DeletedList = ''
        for j in xrange(0, MAX_GROUP_NUM):
          if i * MAX_GROUP_NUM + j >= MemberCount:
            break

          Member = MemberList[i * MAX_GROUP_NUM + j]
          UserNames.append(Member['UserName'])
          NickNames.append(Member['NickName'].encode('utf-8'))

        print '第%s组...' % (i + 1)
        loginfo.append('第%s组...' % (i + 1))
        print ', '.join(NickNames)
        loginfo.append(', '.join(NickNames))

        # 新建群组/添加成员
        if ChatRoomName == '':
          (ChatRoomName, DeletedList) = createChatroom(UserNames)
        else:
          DeletedList = addMember(ChatRoomName, UserNames)

        DeletedCount = len(DeletedList)
        if DeletedCount > 0:
          result += DeletedList

        print '找到%s个被删好友' % DeletedCount
        loginfo.append('找到%s个被删好友' % DeletedCount)
        # raw_input()

        # 删除成员
        deleteMember(ChatRoomName, UserNames)

      # todo 删除群组

      resultNames = []
      for Member in MemberList:
        if Member['UserName'] in result:
          NickName = Member['NickName']
          if Member['RemarkName'] != '':
            NickName += '(%s)' % Member['RemarkName']
          resultNames.append(NickName.encode('utf-8'))

      print '---------- 被删除的好友列表 ----------'
      print '\n'.join(resultNames)
      print '-----------------------------------'
      return resultNames
  except Exception:
    return loginfo

class SearchHandler(tornado.web.RequestHandler):
  def post(self):
    try:
      if waitForLogin() == '408':
        self.render('error.html', title='微信被删好友查询', ex='登录超时, 请确认您已经在微信客户端扫描二维码并登录.')
      elif waitForLogin() == '201':
        self.render('error.html', title='微信被删好友查询', ex='您已扫描二维码, 但并未登录.')
      if login() == False:
        result = ['']
        loginfo2 = ['登录失败']
        print '登录失败'
        self.render('error.html', title='微信被删好友查询',ex=loginfo2)
      else:
        result = loggedRequest()
        self.render('friend.html', title='微信被删好友查询', result=result, loginfo=loginfo)
    except Exception as ex:
      self.render('error.html', title='微信被删好友查询', ex=ex.message)

class HomeHandler(tornado.web.RequestHandler):
  def get(self):
    try:
      opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.CookieJar()))
      urllib2.install_opener(opener)

      if getUUID() == False:
        print '获取uuid失败'
        loginfo.append('获取uuid失败')
        self.render('error.html', title='微信被删好友查询', ex="获取uuid失败")
      url = 'https://login.weixin.qq.com/qrcode/' + uuid
      showQRImage()
      self.render('home.html', title='微信被删好友查询', url=url)
    except Exception as ex:
      self.render('error.html', title='微信被删好友查询', ex=ex.message)


def showQRImage():
  global tip

  #url = 'https://login.weixin.qq.com/qrcode/' + uuid
  #params = {
  #'t': 'webwx',
  #'_': int(time.time()),
  #}

  #request = urllib2.Request(url=url, data=urllib.urlencode(params))
  #response = urllib2.urlopen(request)
  #data = response.read()
  #print data

  tip = 1

def waitForLogin():
  try:
    global tip, base_uri, redirect_uri
    url = 'https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login?tip=%s&uuid=%s&_=%s' % (tip, uuid, int(time.time()))
    request = urllib2.Request(url=url)
    response = urllib2.urlopen(request)
    data = response.read()
    # print data
    # window.code=500;
    regx = r'window.code=(\d+);'
    pm = re.search(regx, data)

    code = pm.group(1)

    if code == '201':  # 已扫描
      print '成功扫描,请在手机上点击确认以登录'
      loginfo.append('成功扫描,请在手机上点击确认以登录')
      tip = 0
    elif code == '200':  # 已登录
      print '正在登录...'
      regx = r'window.redirect_uri="(\S+?)";'
      pm = re.search(regx, data)
      redirect_uri = pm.group(1) + '&fun=new'
      base_uri = redirect_uri[:redirect_uri.rfind('/')]
    elif code == '408':  # 超时
      pass
    # elif code == '400' or code == '500':

    return code
  except Exception:
    return 408

def login():
  try:
    global skey, wxsid, wxuin, pass_ticket, BaseRequest

    request = urllib2.Request(url=redirect_uri)
    response = urllib2.urlopen(request)
    data = response.read()

    # print data

    '''
      <error>
        <ret>0</ret>
        <message>OK</message>
        <skey>xxx</skey>
        <wxsid>xxx</wxsid>
        <wxuin>xxx</wxuin>
        <pass_ticket>xxx</pass_ticket>
        <isgrayscale>1</isgrayscale>
      </error>
    '''

    doc = xml.dom.minidom.parseString(data)
    root = doc.documentElement

    for node in root.childNodes:
      if node.nodeName == 'skey':
        skey = node.childNodes[0].data
      elif node.nodeName == 'wxsid':
        wxsid = node.childNodes[0].data
      elif node.nodeName == 'wxuin':
        wxuin = node.childNodes[0].data
      elif node.nodeName == 'pass_ticket':
        pass_ticket = node.childNodes[0].data

    # print 'skey: %s, wxsid: %s, wxuin: %s, pass_ticket: %s' % (skey, wxsid, wxuin, pass_ticket)

    if skey == '' or wxsid == '' or wxuin == '' or pass_ticket == '':
      return False

    BaseRequest = {
    'Uin': int(wxuin),
    'Sid': wxsid,
    'Skey': skey,
    'DeviceID': deviceId,
    }

    return True
  except Exception:
    return False


def webwxinit():
  try:
    url = base_uri + '/webwxinit?pass_ticket=%s&skey=%s&r=%s' % (pass_ticket, skey, int(time.time()))
    params = {
    'BaseRequest': BaseRequest
    }

    request = urllib2.Request(url=url, data=json.dumps(params))
    request.add_header('ContentType', 'application/json; charset=UTF-8')
    response = urllib2.urlopen(request)
    data = response.read()

    if DEBUG == True:
      f = open(os.getcwd() + '/webwxinit.json', 'wb')
      f.write(data)
      f.close()

    # print data

    global ContactList, My
    dic = json.loads(data)
    ContactList = dic['ContactList']
    My = dic['User']

    ErrMsg = dic['BaseResponse']['ErrMsg']
    if len(ErrMsg) > 0:
      print ErrMsg

    Ret = dic['BaseResponse']['Ret']
    if Ret != 0:
      return False

    return True
  except Exception:
    return False

def webwxgetcontact():
  url = base_uri + '/webwxgetcontact?pass_ticket=%s&skey=%s&r=%s' % (pass_ticket, skey, int(time.time()))

  request = urllib2.Request(url=url)
  request.add_header('ContentType', 'application/json; charset=UTF-8')
  response = urllib2.urlopen(request)
  data = response.read()

  if DEBUG == True:
    f = open(os.getcwd() + '/webwxgetcontact.json', 'wb')
    f.write(data)
    f.close()

  # print data

  dic = json.loads(data)
  MemberList = dic['MemberList']

  # 倒序遍历,不然删除的时候出问题..
  SpecialUsers = ['newsapp', 'fmessage', 'filehelper', 'weibo', 'qqmail', 'fmessage', 'tmessage', 'qmessage', 'qqsync',
                  'floatbottle', 'lbsapp', 'shakeapp', 'medianote', 'qqfriend', 'readerapp', 'blogapp', 'facebookapp',
                  'masssendapp', 'meishiapp', 'feedsapp', 'voip', 'blogappweixin', 'weixin', 'brandsessionholder',
                  'weixinreminder', 'wxid_novlwrv3lqwv11', 'gh_22b87fa7cb3c', 'officialaccounts',
                  'notification_messages', 'wxid_novlwrv3lqwv11', 'gh_22b87fa7cb3c', 'wxitil', 'userexperience_alarm',
                  'notification_messages']
  for i in xrange(len(MemberList) - 1, -1, -1):
    Member = MemberList[i]
    if Member['VerifyFlag'] & 8 != 0:  # 公众号/服务号
      MemberList.remove(Member)
    elif Member['UserName'] in SpecialUsers:  # 特殊账号
      MemberList.remove(Member)
    elif Member['UserName'].find('@@') != -1:  # 群聊
      MemberList.remove(Member)
    elif Member['UserName'] == My['UserName']:  # 自己
      MemberList.remove(Member)

  return MemberList


def createChatroom(UserNames):
  MemberList = []
  for UserName in UserNames:
    MemberList.append({'UserName': UserName})

  url = base_uri + '/webwxcreatechatroom?pass_ticket=%s&r=%s' % (pass_ticket, int(time.time()))
  params = {
  'BaseRequest': BaseRequest,
  'MemberCount': len(MemberList),
  'MemberList': MemberList,
  'Topic': '',
  }

  request = urllib2.Request(url=url, data=json.dumps(params))
  request.add_header('ContentType', 'application/json; charset=UTF-8')
  response = urllib2.urlopen(request)
  data = response.read()

  # print data

  dic = json.loads(data)
  ChatRoomName = dic['ChatRoomName']
  MemberList = dic['MemberList']
  DeletedList = []
  for Member in MemberList:
    if Member['MemberStatus'] == 4:  # 被对方删除了
      DeletedList.append(Member['UserName'])

  ErrMsg = dic['BaseResponse']['ErrMsg']
  if len(ErrMsg) > 0:
    print ErrMsg

  return (ChatRoomName, DeletedList)


def deleteMember(ChatRoomName, UserNames):
  url = base_uri + '/webwxupdatechatroom?fun=delmember&pass_ticket=%s' % (pass_ticket)
  params = {
  'BaseRequest': BaseRequest,
  'ChatRoomName': ChatRoomName,
  'DelMemberList': ','.join(UserNames),
  }

  request = urllib2.Request(url=url, data=json.dumps(params))
  request.add_header('ContentType', 'application/json; charset=UTF-8')
  response = urllib2.urlopen(request)
  data = response.read()

  # print data

  dic = json.loads(data)
  ErrMsg = dic['BaseResponse']['ErrMsg']
  if len(ErrMsg) > 0:
    print ErrMsg

  Ret = dic['BaseResponse']['Ret']
  if Ret != 0:
    return False

  return True


def addMember(ChatRoomName, UserNames):
  url = base_uri + '/webwxupdatechatroom?fun=addmember&pass_ticket=%s' % (pass_ticket)
  params = {
  'BaseRequest': BaseRequest,
  'ChatRoomName': ChatRoomName,
  'AddMemberList': ','.join(UserNames),
  }

  request = urllib2.Request(url=url, data=json.dumps(params))
  request.add_header('ContentType', 'application/json; charset=UTF-8')
  response = urllib2.urlopen(request)
  data = response.read()

  # print data

  dic = json.loads(data)
  MemberList = dic['MemberList']
  DeletedList = []
  for Member in MemberList:
    if Member['MemberStatus'] == 4:  # 被对方删除了
      DeletedList.append(Member['UserName'])

  ErrMsg = dic['BaseResponse']['ErrMsg']
  if len(ErrMsg) > 0:
    print ErrMsg

  return DeletedList

# windows下编码问题修复
# http://blog.csdn.net/heyuxuanzee/article/details/8442718
class UnicodeStreamFilter:
  def __init__(self, target):
    self.target = target
    self.encoding = 'utf-8'
    self.errors = 'replace'
    self.encode_to = self.target.encoding

  def write(self, s):
    if type(s) == str:
      s = s.decode('utf-8')
    s = s.encode(self.encode_to, self.errors).decode(self.encode_to)
    self.target.write(s)


if sys.stdout.encoding == 'cp936':
  sys.stdout = UnicodeStreamFilter(sys.stdout)
