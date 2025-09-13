from django.shortcuts import redirect
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin

class Home(View, LoginRequiredMixin):
    def get(self, request, *args, **kwargs):
        return redirect("/pos/home")