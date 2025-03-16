from itertools import product
import json
import os
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.http import JsonResponse, HttpResponseRedirect
from django.template.loader import get_template
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, DeleteView, UpdateView, View
from weasyprint import HTML, CSS

from core.erp.forms import SaleForm, ClientForm
from core.erp.mixins import ValidatePermissionRequiredMixin
from core.erp.models import Sale, Product, DetSale, Client, CreditSale


class SaleListView(LoginRequiredMixin, ValidatePermissionRequiredMixin, ListView):
    model = Sale
    template_name = 'sale/list.html'
    permission_required = 'view_sale'

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'searchdata':
                data = []
                for i in Sale.objects.all():
                    data.append(i.toJSON())
            elif action == 'search_details_prod':
                data = []
                for i in DetSale.objects.filter(sale_id=request.POST['id']):
                    data.append(i.toJSON())
            else:
                data['error'] = 'Ha ocurrido un error'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Listado de Ventas'
        context['create_url'] = reverse_lazy('erp:sale_create')
        context['list_url'] = reverse_lazy('erp:sale_list')
        context['entity'] = 'Ventas'
        return context


class SaleCreateView(LoginRequiredMixin, ValidatePermissionRequiredMixin, CreateView):
    model = Sale
    form_class = SaleForm
    template_name = 'sale/create.html'
    success_url = reverse_lazy('erp:sale_list')
    permission_required = 'add_sale'
    url_redirect = success_url

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'search_products':
                data = []
                ids_exclude = json.loads(request.POST['ids'])
                term = request.POST['term'].strip()
                products = Product.objects.filter(stock__gt=0)
                if len(term):
                    products = products.filter(name__icontains=term)
                for i in products.exclude(id__in=ids_exclude)[0:10]:
                    item = i.toJSON()
                    item['value'] = i.name
                    # item['text'] = i.name
                    data.append(item)
            elif action == 'search_autocomplete':
                data = []
                ids_exclude = json.loads(request.POST['ids'])
                term = request.POST['term'].strip()
                data.append({'id': term, 'text': term})
                products = Product.objects.filter(name__icontains=term, stock__gt=0)
                for i in products.exclude(id__in=ids_exclude)[0:10]:
                    item = i.toJSON()
                    item['text'] = i.name
                    data.append(item)
            elif action == 'add':
                with transaction.atomic():
                    vents = json.loads(request.POST['vents'])
                    print(vents)
                    sale = Sale()
                    sale.date_joined = vents['date_joined']
                    sale.cli_id = vents['cli']
                    sale.subtotal = float(vents['subtotal'])
                    sale.iva = float(vents['iva'])
                    sale.discountall = float(vents['discountall'])
                    sale.total = float(vents['total'])
                    sale.type_payment = vents['type_payment']
                    sale.down_payment = float(vents['down_payment'])
                    sale.observation = vents['observation']
                    sale.save()
                    for i in vents['products']:
                        det = DetSale()
                        det.sale_id = sale.id
                        det.prod_id = i['id']
                        det.cant = int(i['cant'])
                        det.price = float(i['pvp'])
                        det.discount = float(i['discount'])
                        det.subtotal = float(i['subtotal'])
                        det.save()
                        det.prod.stock -= det.cant
                        det.prod.save()
                    data = {'id': sale.id}
                    if vents['type_payment'] == 'CREDIT':
                        credsale = CreditSale()
                        credsale.sale_id = sale.id
                        credsale.total_credit = sale.total
                        credsale.down_payment = sale.down_payment
                        credsale.save()
            elif action == 'search_clients':
                data = []
                term = request.POST['term']
                clients = Client.objects.filter(
                    Q(names__icontains=term) | Q(surnames__icontains=term) | Q(dni__icontains=term))[0:10]
                for i in clients:
                    item = i.toJSON()
                    item['text'] = i.get_full_name()
                    data.append(item)
            elif action == 'create_client':
                with transaction.atomic():
                    frmClient = ClientForm(request.POST)
                    data = frmClient.save()
            else:
                data['error'] = 'No ha ingresado a ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Creación de una Venta'
        context['entity'] = 'Ventas'
        context['list_url'] = self.success_url
        context['action'] = 'add'
        context['det'] = []
        context['frmClient'] = ClientForm()
        return context


class SaleUpdateView(LoginRequiredMixin, ValidatePermissionRequiredMixin, UpdateView):
    model = Sale
    form_class = SaleForm
    template_name = 'sale/create.html'
    success_url = reverse_lazy('erp:sale_list')
    permission_required = 'change_sale'
    url_redirect = success_url

    def get_form(self, form_class=None):
        instance = self.get_object()
        form = SaleForm(instance=instance)
        form.fields['cli'].queryset = Client.objects.filter(id=instance.cli.id)
        return form

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            action = request.POST['action']
            if action == 'search_products':
                data = []
                ids_exclude = json.loads(request.POST['ids'])
                term = request.POST['term'].strip()
                products = Product.objects.filter(stock__gt=0)
                if len(term):
                    products = products.filter(name__icontains=term)
                for i in products.exclude(id__in=ids_exclude)[0:10]:
                    item = i.toJSON()
                    item['value'] = i.name
                    # item['text'] = i.name
                    data.append(item)
            elif action == 'search_autocomplete':
                data = []
                ids_exclude = json.loads(request.POST['ids'])
                term = request.POST['term'].strip()
                data.append({'id': term, 'text': term})
                products = Product.objects.filter(name__icontains=term, stock__gt=0)
                for i in products.exclude(id__in=ids_exclude)[0:10]:
                    item = i.toJSON()
                    item['text'] = i.name
                    data.append(item)
            elif action == 'edit':
                with transaction.atomic():
                    vents = json.loads(request.POST['vents'])
                    # sale = Sale.objects.get(pk=self.get_object().id)
                    sale = self.get_object()
                    sale.date_joined = vents['date_joined']
                    sale.cli_id = vents['cli']
                    sale.subtotal = float(vents['subtotal'])
                    sale.iva = float(vents['iva'])
                    sale.discountall = float(vents['discountall'])
                    sale.total = float(vents['total'])
                    sale.type_payment = vents['type_payment']
                    sale.down_payment = vents['down_payment']
                    if vents['type_payment'] == 'CASH':
                        sale.down_payment = vents['total']
                    sale.observation = vents['observation']
                    sale.save()
                    sale.detsale_set.all().delete()
                    for i in vents['products']:
                        det = DetSale()
                        det.sale_id = sale.id
                        det.prod_id = i['id']
                        det.cant = int(i['cant'])
                        det.price = float(i['pvp'])
                        det.discount = float(i['discount'])
                        det.subtotal = float(i['subtotal'])
                        det.save()
                        det.prod.stock -= det.cant
                        det.prod.save()
                    if vents['type_payment'] == 'CREDIT':
                        CreditSale.objects.filter(sale_id=sale.id).delete()
                        credsale = CreditSale()
                        credsale.sale_id = sale.id
                        credsale.total_credit = sale.total
                        credsale.down_payment = sale.down_payment
                        credsale.save()
                    data = {'id': sale.id}
            elif action == 'search_clients':
                data = []
                term = request.POST['term']
                clients = Client.objects.filter(
                    Q(names__icontains=term) | Q(surnames__icontains=term) | Q(dni__icontains=term))[0:10]
                for i in clients:
                    item = i.toJSON()
                    item['text'] = i.get_full_name()
                    data.append(item)
            elif action == 'create_client':
                with transaction.atomic():
                    frmClient = ClientForm(request.POST)
                    data = frmClient.save()
            else:
                data['error'] = 'No ha ingresado a ninguna opción'
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data, safe=False)

    def get_details_product(self):
        data = []
        try:
            for i in DetSale.objects.filter(sale_id=self.get_object().id):
                item = i.prod.toJSON()
                item['cant'] = i.cant
                item['discount'] = i.discount
                data.append(item)
        except:
            pass
        return data

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edición de una Venta'
        context['entity'] = 'Ventas'
        context['list_url'] = self.success_url
        context['action'] = 'edit'
        context['det'] = json.dumps(self.get_details_product())
        context['frmClient'] = ClientForm()
        return context

class SaleDeleteView(LoginRequiredMixin, ValidatePermissionRequiredMixin, DeleteView):
    model = Sale
    template_name = 'sale/delete.html'
    success_url = reverse_lazy('erp:sale_list')
    permission_required = 'delete_sale'
    url_redirect = success_url

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = {}
        try:
            self.object.delete()
        except Exception as e:
            data['error'] = str(e)
        return JsonResponse(data)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Eliminación de una Venta'
        context['entity'] = 'Ventas'
        context['list_url'] = self.success_url
        return context


class SaleInvoicePdfView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        try:
            template = get_template('sale/invoice.html')
            
            # Obtener la venta
            sale = get_object_or_404(Sale, pk=self.kwargs['pk'])

            # Obtener detalles de venta y calcular el descuento total
            details = sale.detsale_set.all().values('prod__name', 'price', 'cant', 'discount', 'subtotal')
            
            products_discount=0
            balance = 0

            # Convertir QuerySet a lista y calcular el descuento total
            details = list(details)
            for item in details:
                item['p_discount'] = (item['price'] * item['cant']) - item['subtotal'] # Multiplicación del descuento por la cantidad
                item['total_val'] = (item['price'] * item['cant']) # Multiplicación del descuento por la cantidad
                products_discount += item['p_discount']

            sale.discountall = sale.discountall + products_discount
            sale.subtotal = sale.subtotal + products_discount
            balance = sale.total - sale.down_payment
            context = {
                'balance': balance,
                'sale': sale,
                'details':details,
                'comp': {'name': 'AGROINSUMOS MERKO SUR', 'nit': '1085928681-1', 'address': 'La Victoria', 'city': 'Ipiales', 'vendor': 'Alexander Palles'},
                'icon': '{}{}'.format(settings.MEDIA_URL, 'logo.png')
            }

            html = template.render(context)
            css_url = os.path.join(settings.BASE_DIR, 'static/lib/bootstrap-4.6.0/css/bootstrap.min.css')
            pdf = HTML(string=html, base_url=request.build_absolute_uri()).write_pdf(stylesheets=[CSS(css_url)])
            return HttpResponse(pdf, content_type='application/pdf')
        except:
            pass
        return HttpResponseRedirect(reverse_lazy('erp:sale_list'))
