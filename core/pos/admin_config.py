from django.contrib import admin
from django import forms
from django.core.files.storage import default_storage
from constance import config
from constance.admin import ConstanceAdmin, ConstanceForm
from django.shortcuts import render
from django.http import HttpResponseRedirect

class LogoUploadForm(forms.Form):
    logo = forms.ImageField(
        label='Logo del Negocio',
        help_text='Sube una imagen para usar como logo (PNG, JPG, JPEG)',
        required=False
    )

# Personalización opcional del admin de Constance
# Se puede extender más adelante si se necesita
