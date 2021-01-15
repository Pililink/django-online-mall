from django.shortcuts import render

# Create your views here.

#/index
def index(request):
    '''首页'''
    return  render(request,'index.html')

#/login
def login(request):
    '''首页'''
    return  render(request,'login.html')