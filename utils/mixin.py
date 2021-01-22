from django.contrib.auth.decorators import login_required

class LoginRequiredMixin(object):
    @classmethod
    def as_view(cls,**initkwargs):
        #调用父类的as_view
        view = super(LoginRequiredMixin, cls).as_view(**initkwargs)
        return login_required(view)
'''
Mixin原理（as_view的继承关系）：
例如：
    url：
    path('',UserInfoView.as_view(),name='user')# 用户中心信息页
    
    views:
    class UserInfoView(LoginRequiredMixin,View):
        def get(self,request):
            return render(request,'user/user_center_info.html',{'page':"user"})
            
这个url信息中 UserInfoView 这个试图方法中没有as_view()这个方法，因此会调用父类的这个方法
因为LoginRequiredMixin写在View前面，会先调用LoginRequiredMixin中的as_view()方法。
LoginRequiredMixin主要实现的是一个装饰器的功能，
    
    view = super(LoginRequiredMixin, cls).as_view(**initkwargs)
这个语句中super会调视图方法后面的View中的as_view()方法，并将返回值保持下来。
    return login_required(view)
返回时加上login_required进行判断。
'''