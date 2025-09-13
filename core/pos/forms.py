from django import forms
from django.contrib.auth.forms import UserChangeForm,UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.models import Group

from .models import CategoriasProductos, Producto, ValorDolar


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre','cantidad', 'unidad','moneda', 'imagen', 'barcode', 'costo', 'precio_detal','categoria','subproducto','relacion_subproducto']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el nombre del producto'
            }),
            'cantidad': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Cantidad disponible',
                'min': '0',
                'step': '0.01'
            }),
            'unidad': forms.Select(choices=Producto.UNIDAD_OPCIONES, attrs={
                'class': 'form-select'
            }),
            'moneda': forms.Select(choices=Producto.MONEDA_OPCIONES, attrs={
                'class': 'form-select'
            }),
            'imagen': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'barcode': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Código de barras (opcional)'
            }),
            'costo': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Precio de costo',
                'min': '0',
                'step': '0.01'
            }),
            'precio_detal': forms.NumberInput(attrs={
                 'class': 'form-control',
                 'placeholder': 'Precio al detal',
                 'min': '0',
                 'step': '0.01'
             }),
            'relacion_subproducto': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Relación con subproducto',
                'min': '0',
                'step': '0.01'
            })
        }
    
    subproducto = forms.ModelChoiceField(
        queryset=Producto.objects.all().order_by("nombre"),
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    categoria = forms.ModelMultipleChoiceField(
        queryset=CategoriasProductos.objects.all(),
        widget=forms.CheckboxSelectMultiple,
    )

    def form_valid(self, form):
        # Asignar las categorías al producto antes de guardarlo
        self.object = form.save(commit=False)
        self.object.save()
        form.save_m2m()
        return super().form_valid(form)
   
    def save(self, commit=True):
        instancia = super().save(commit=False)
        if commit:
            instancia.save()
        instancia.categoria.set(self.cleaned_data['categoria'])
        return instancia

class CustomUserCreationForm(UserCreationForm):
    username = forms.CharField(
        label='Nombre de usuario',
        strip=False,
        help_text='Este será tu nombre de usuario. Puede contener letras, números y caracteres especiales.',
    )
    first_name = forms.CharField(label='Nombre', max_length=30, required=True)
    last_name = forms.CharField(label='Apellido', max_length=30, required=True)
    
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'password1', 'password2')
        labels = {
            'password1': 'Contraseña',
            'password2': 'Confirmar contraseña',
        }


class ModificarUsuarioForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'groups')
        labels = {
            'username': 'Nombre de usuario',
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'groups': 'Grupo',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop('password')
        self.fields['username'].help_text = ''
        self.fields['first_name'].help_text = ''
        self.fields['last_name'].help_text = ''
        self.fields['groups'].help_text = ''


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = CategoriasProductos
        fields = ['nombre', 'imagen', 'orden']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el nombre de la categoría'
            }),
            'imagen': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'orden': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Orden de visualización',
                'min': '1',
                'step': '1'
            })
        }

class ValorDolarForm(forms.ModelForm):
    """
    Formulario para crear o actualizar el valor del dólar
    """
    class Meta:
        model = ValorDolar
        fields = ['valor']
        labels = {
            'valor': 'Valor del Dólar (Bs.)',
        }
        widgets = {
            'valor': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ingrese el valor del dólar en bolívares',
                'step': '0.01',
                'min': '0.01',
            })
        }
    
    def clean_valor(self):
        """
        Validar que el valor del dólar sea positivo
        """
        valor = self.cleaned_data.get('valor')
        if valor is not None and valor <= 0:
            raise forms.ValidationError('El valor del dólar debe ser mayor a cero.')
        return valor